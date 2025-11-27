
# Import langchain modules
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# Import MistralOCR
from mistralai import Mistral
from mistralai import DocumentURLChunk, ImageURLChunk
from mistralai.models import OCRResponse

import os
import time
import uuid
import hashlib
import tempfile
import base64
from datetime import datetime
from typing import List, Optional, Any

# Environment & Type Hinting
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load Gemini API and Mistral OCR
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Configurations ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MISTRAL_FILE_LIMIT_MB = 50
MAX_REQUESTS_PER_MINUTE = 20

class RateLimitTracker:
    """Tracks API usage to prevent hitting rate limits."""
    def __init__(self, limit: int = MAX_REQUESTS_PER_MINUTE):
        self.requests_made = 0
        self.last_reset = time.time()
        self.limit = limit
        
    def wait_if_needed(self):
        current_time = time.time()
        # Reset counter if a minute has passed
        if current_time - self.last_reset >= 60:
            self.requests_made = 0
            self.last_reset = current_time
            
        # Check limit
        if self.requests_made >= self.limit:
            wait_time = 60 - (current_time - self.last_reset) + 1
            print(f"⏳ Rate limit hit. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            self.requests_made = 0
            self.last_reset = time.time()
            
        self.requests_made += 1

rate_tracker = RateLimitTracker()

# Prompt template
PROMPT_TEMPLATE = """
You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, say that you don't know. DON'T MAKE UP ANYTHING.

{context}

---

Answer the question based on the above context: {query}
"""

# --- Helper functions ---
def get_mistral_client():
    """Initialize client dynamically to catch Streamlit input"""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return None
    return Mistral(api_key=api_key)

def get_gemini_llm():
    """Initialize LLM dynamically to catch Streamlit input"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7, google_api_key=api_key)

def print_api_metrics(client, file_path=None):
    """Print comprehensive API metrics and quota information"""
    print("\n" + "="*60)
    print("📊 API METRICS & QUOTA INFORMATION")
    print("="*60)
    
    # File information
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        print(f"📄 File: {os.path.basename(file_path)}")
        print(f"   Size: {file_size} bytes ({file_size/1024:.1f}KB, {file_size/(1024*1024):.2f}MB)")
        print(f"   Type: PDF")
    
    # Rate limit info
    current = rate_tracker.requests_made
    max_limit = rate_tracker.limit
    print(f"🔄 Rate Limits:")
    print(f"   Current request: {current}/{max_limit} per minute")
    print(f"   Remaining: {max_limit - current} requests")
    
    # Mistral API specific validations
    print(f"🔍 Mistral OCR Validations:")
    print(f"   Max file size: 10MB")
    print(f"   Supported formats: PDF, PNG, JPG, JPEG")
    print(f"   Document requirements: Standard PDF format")
    
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")

def upload_pdf(client: Mistral, file_path: str) -> str:
    """Uploads file to Mistral and returns a signed URL."""
    filename = os.path.basename(file_path)
    
    # Rate limit check
    rate_tracker.wait_if_needed()
    
    print(f"📤 Uploading {filename} to Mistral...")
    with open(file_path, "rb") as f:
        file_upload = client.files.upload(
            file={"file_name": filename, "content": f},
            purpose = "ocr"
        )
    
    # Get signed URL
    signed_url = client.files.get_signed_url(file_id=file_upload.id)
    return signed_url.url

def load_and_chunk(path):
    loader = PyPDFLoader(path)
    pages = loader.load()

    # Split document
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " "]
    )
    
    chunks = text_splitter.split_documents(pages)
    return chunks

def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    """
    Replaces Mistral's markdown image placeholders with Base64 data URIs.
    Standard Mistral output: ![id](id)
    Target output: ![id](data:image/jpeg;base64,...)
    """
    for img_name, base64_str in images_dict.items():
        mistral_pattern = f"![{img_name}]({img_name})"
        # Standard markdwon Data URL
        replacement = f"![{img_name}](data:image/jpeg;base64,{base64_str})"
        markdown_str = markdown_str.replace(mistral_pattern, replacement)

    return markdown_str

def process_mistral_ocr(file_path):
    """Process document with Mistral OCR"""
    client = get_mistral_client()
    if not client: 
        return []
    try:      
        signed_url = upload_pdf(client, file_path)
        rate_tracker.wait_if_needed()        
        # Process OCR with metrics
        current = rate_tracker.requests_made
        max_limit = rate_tracker.limit
        print(f"🔍 API Request {current}/{max_limit} - Starting OCR processing")
        
        ocr_response = client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url),
            model="mistral-ocr-latest",
            include_image_base64=True
        )
              
        # Convert to markdown and chunk
        markdowns = []
        for page in ocr_response.pages:
            image_data = {img.id: img.image_base64 for img in page.images}
            # Fix image links in markdown
            page_md = replace_images_in_markdown(page.markdown, image_data)
            markdowns.append(page_md)
            
        full_text = "\n\n".join(markdowns)
        
        # Create document from OCR result
        ocr_doc = Document(
            page_content=full_text,
            metadata={"source": file_path, "processing_method": "mistral_ocr"}
        )
        
        # Chunk the OCR result
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, 
            chunk_overlap=CHUNK_OVERLAP
        )
        
        ocr_chunks = text_splitter.split_documents([ocr_doc])        
        print(f"✅ OCR processing completed successfully")
        print(f"Pages processed: {len(ocr_response.pages)}")
        print(f"✅ Created {len(ocr_chunks)} OCR chunks")
        return ocr_chunks
        
    except Exception as e:
        print(f"❌ OCR processing failed: {e}")
        # Print final metrics after failure
        current = rate_tracker.requests_made
        max_limit = rate_tracker.limit
        print("📊 Final API metrics:")
        print(f"Requests made this minute: {current}/{max_limit}")
        print(f"   Remaining requests: {max_limit - current}")
        
        return []
    
# --- Base case (OCR fails to run) ---
def process_standard_pdf(file_path: str) -> List[Document]:
    """Fallback text extraction using PyPDF."""
    print("📖 Extracting text using PyPDF (Fallback)...")
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    return splitter.split_documents(pages)

# --- Main Processing Pipeline ---
def process_medical_document(file_path):
    """Main processing pipeline for medical documents"""
    chunks = []
    mistral_client = get_mistral_client()

    # Print file info
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
    print(f"📄 Processing document: {os.path.basename(file_path)} ({file_size:.2f}MB)")
    
    if mistral_client and file_size <= MISTRAL_FILE_LIMIT_MB:
        chunks = process_mistral_ocr(file_path)
    
    # Fallback: If OCR failed or wasn't attempted, use standard loader
    if not chunks:
        if file_size > MISTRAL_FILE_LIMIT_MB:
            print(f"⚠️ File too large for OCR ({file_size:.2f}MB). Using standard text extraction.")
        chunks = process_standard_pdf(file_path)

    # Add Metadata
    for chunk in chunks:
        chunk.metadata.update({
            "doc_id": str(uuid.uuid4()),
            "chunk_hash": hashlib.md5(chunk.page_content.encode()).hexdigest()[:8]
        })
        
    print(f"✅ Final processing complete. Generated {len(chunks)} chunks.")
    return chunks

def format_docs(docs):
    return "\n\n --- \n\n".join([doc.page_content for doc in docs])

def get_embedding_function():
    # api_key = os.getenv("GEMINI_API_KEY")
    # if not GEMINI_API_KEY:
    #     raise ValueError("Gemini API key not configured")
    
    # embeddings = GoogleGenerativeAIEmbeddings(
    #     model="models/gemini-embedding-001", 
    #     google_api_key=api_key,
    #     task_type="retrieval_document",
    #     output_dimensionality = 1536
    # )
    model_name = "sentence-transformers/all-mpnet-base-v2"
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    return embeddings

def create_vectorstore(chunks, embedding_function, vectorstore_path):   
    # Create a list of unique ids for each document based on the content
    ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, doc.page_content)) for doc in chunks]

    # Ensure that only unique docs with unique ids are kept
    unique_ids = set()
    unique_chunks = []
    BATCH_SIZE = 100

    for chunk, id in zip(chunks, ids):
        if id not in unique_ids:
            unique_ids.add(id)
            unique_chunks.append(chunk)

    print(f"🔧 Creating vector store with {len(unique_chunks)} unique chunks...")
    
    # Create new Chroma database from the documents

    vectorstore = Chroma(
        embedding_function=embedding_function,
        persist_directory=vectorstore_path
    )

    for i in range(0, len(unique_chunks), BATCH_SIZE):
        batch = unique_chunks[i: i + BATCH_SIZE]
        current_batch = (i // BATCH_SIZE) + 1
        try: 
            vectorstore.add_documents(batch)
            time.sleep(5)
            print(f"Completed batch {current_batch}: Total {i + BATCH_SIZE} chunks have been embedded.")
        except Exception as e:
            print(f"   ❌ Error on batch {current_batch}: {e}")
            # Optional: You could add a longer sleep and retry logic here
            raise e

    print("✅ Vector store created successfully")
    return vectorstore

def generate_response(query: str, vectorstore):  
    """Generate response using RAG chain"""
    llm = get_gemini_llm()
    if not llm:
        raise ValueError("Gemini LLM not initialized")
    
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)  

    # Create retriever 
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    
    rag_chain = (
        {"context": retriever | format_docs, "query": RunnablePassthrough()}
        | prompt_template
        | llm
    )

    return rag_chain.invoke(query)

def main():
    print("Medical OCR Processor - Use streamlit_app.py to run the application")
    print(f"API Status - Gemini: {'✅' if GEMINI_API_KEY else '❌'}, Mistral: {'✅' if MISTRAL_API_KEY else '❌'}")
if __name__ == "__main__":
    main()