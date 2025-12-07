# =========================
# IMPORT DEPENDENCIES
# =========================

# Import LangChain core modules
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# Import Mistral OCR modules
from mistralai import Mistral
from mistralai import DocumentURLChunk, ImageURLChunk
from mistralai.models import OCRResponse

# System & utility libraries
import os
import time
import uuid
import hashlib
import tempfile
import base64
from datetime import datetime
from typing import List, Optional, Any

# Environment & validation
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# =========================
# LOAD API KEYS
# =========================

# Load environment variables from .env file
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# =========================
# CONFIGURATION SETTINGS
# =========================

CHUNK_SIZE = 1000                 # Number of characters per text chunk
CHUNK_OVERLAP = 200               # Overlap between consecutive chunks
MISTRAL_FILE_LIMIT_MB = 50        # Maximum file size supported for Mistral OCR
MAX_REQUESTS_PER_MINUTE = 20      # API rate limit

# =========================
# RATE LIMIT TRACKER
# =========================

class RateLimitTracker:
    """Tracks API requests to avoid exceeding rate limits."""
    
    def __init__(self, limit: int = MAX_REQUESTS_PER_MINUTE):
        self.requests_made = 0
        self.last_reset = time.time()
        self.limit = limit
        
    def wait_if_needed(self):
        """Waits if the current request exceeds the per-minute limit."""
        current_time = time.time()

        # Reset counter after 60 seconds
        if current_time - self.last_reset >= 60:
            self.requests_made = 0
            self.last_reset = current_time
            
        # Enforce rate limit
        if self.requests_made >= self.limit:
            wait_time = 60 - (current_time - self.last_reset) + 1
            print(f"⏳ Rate limit hit. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            self.requests_made = 0
            self.last_reset = time.time()
            
        self.requests_made += 1

rate_tracker = RateLimitTracker()

# =========================
# PROMPT TEMPLATE FOR RAG
# =========================

PROMPT_TEMPLATE = """
You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, say that you don't know. DON'T MAKE UP ANYTHING.

{context}

---

Answer the question based on the above context: {query}
"""

# =========================
# HELPER FUNCTIONS
# =========================

def get_mistral_client():
    """Initialize Mistral client dynamically."""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return None
    return Mistral(api_key=api_key)

def get_gemini_llm():
    """Initialize Gemini LLM dynamically."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
        google_api_key=api_key
    )

def print_api_metrics(client, file_path=None):
    """Print API usage, file info, and request limit details."""
    print("\n" + "="*60)
    print("📊 API METRICS & QUOTA INFORMATION")
    print("="*60)
    
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        print(f"📄 File: {os.path.basename(file_path)}")
        print(f"   Size: {file_size} bytes ({file_size/1024:.1f}KB, {file_size/(1024*1024):.2f}MB)")
        print(f"   Type: PDF")
    
    current = rate_tracker.requests_made
    max_limit = rate_tracker.limit
    print(f"🔄 Rate Limits:")
    print(f"   Current request: {current}/{max_limit} per minute")
    print(f"   Remaining: {max_limit - current} requests")
    
    print(f"🔍 Mistral OCR Validations:")
    print(f"   Max file size: 10MB")
    print(f"   Supported formats: PDF, PNG, JPG, JPEG")
    print(f"   Document requirements: Standard PDF format")
    
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")

# =========================
# OCR UPLOAD & PROCESSING
# =========================

def upload_pdf(client: Mistral, file_path: str) -> str:
    """Upload PDF to Mistral and return a signed URL."""
    filename = os.path.basename(file_path)
    
    rate_tracker.wait_if_needed()
    
    print(f"📤 Uploading {filename} to Mistral...")
    with open(file_path, "rb") as f:
        file_upload = client.files.upload(
            file={"file_name": filename, "content": f},
            purpose="ocr"
        )
    
    signed_url = client.files.get_signed_url(file_id=file_upload.id)
    return signed_url.url

def load_and_chunk(path):
    """Load PDF and split into smaller chunks."""
    loader = PyPDFLoader(path)
    pages = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " "]
    )
    
    chunks = text_splitter.split_documents(pages)
    return chunks

def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    """Replace Mistral placeholder images with Base64 encoded images."""
    for img_name, base64_str in images_dict.items():
        mistral_pattern = f"![{img_name}]({img_name})"
        replacement = f"![{img_name}](data:image/jpeg;base64,{base64_str})"
        markdown_str = markdown_str.replace(mistral_pattern, replacement)
    return markdown_str

def process_mistral_ocr(file_path):
    """Process document using Mistral OCR."""
    client = get_mistral_client()
    if not client: 
        return []
    
    try:
        signed_url = upload_pdf(client, file_path)
        rate_tracker.wait_if_needed()        

        print(f"🔍 API Request {rate_tracker.requests_made}/{rate_tracker.limit} - Starting OCR processing")
        
        ocr_response = client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url),
            model="mistral-ocr-latest",
            include_image_base64=True
        )
              
        markdowns = []
        for page in ocr_response.pages:
            image_data = {img.id: img.image_base64 for img in page.images}
            page_md = replace_images_in_markdown(page.markdown, image_data)
            markdowns.append(page_md)
            
        full_text = "\n\n".join(markdowns)
        
        ocr_doc = Document(
            page_content=full_text,
            metadata={"source": file_path, "processing_method": "mistral_ocr"}
        )
        
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
        print("📊 Final API metrics:")
        print(f"Requests made this minute: {rate_tracker.requests_made}/{rate_tracker.limit}")
        return []

# =========================
# FALLBACK PDF PROCESSING
# =========================

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

# =========================
# MAIN PROCESSING PIPELINE
# =========================

def process_medical_document(file_path):
    """Main pipeline for medical document ingestion."""
    chunks = []
    mistral_client = get_mistral_client()

    file_size = os.path.getsize(file_path) / (1024 * 1024)
    print(f"📄 Processing document: {os.path.basename(file_path)} ({file_size:.2f}MB)")
    
    if mistral_client and file_size <= MISTRAL_FILE_LIMIT_MB:
        chunks = process_mistral_ocr(file_path)
    
    if not chunks:
        if file_size > MISTRAL_FILE_LIMIT_MB:
            print(f"⚠️ File too large for OCR. Using standard extraction.")
        chunks = process_standard_pdf(file_path)

    for chunk in chunks:
        chunk.metadata.update({
            "doc_id": str(uuid.uuid4()),
            "chunk_hash": hashlib.md5(chunk.page_content.encode()).hexdigest()[:8]
        })
        
    print(f"✅ Final processing complete. Generated {len(chunks)} chunks.")
    return chunks

# =========================
# VECTOR STORE & EMBEDDING
# =========================

def format_docs(docs):
    return "\n\n --- \n\n".join([doc.page_content for doc in docs])

def get_embedding_function():
    """Load HuggingFace embedding model."""
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
    """Create Chroma DB from processed document chunks."""
    ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, doc.page_content)) for doc in chunks]

    unique_ids = set()
    unique_chunks = []
    BATCH_SIZE = 100

    for chunk, id in zip(chunks, ids):
        if id not in unique_ids:
            unique_ids.add(id)
            unique_chunks.append(chunk)

    print(f"🔧 Creating vector store with {len(unique_chunks)} unique chunks...")
    
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
            print(f"Completed batch {current_batch}: Total {i + BATCH_SIZE} chunks processed.")
        except Exception as e:
            print(f"   ❌ Error on batch {current_batch}: {e}")
            raise e

    print("✅ Vector store created successfully")
    return vectorstore

# =========================
# RAG RESPONSE GENERATION
# =========================

def generate_response(query: str, vectorstore):  
    """Generate answer using RAG pipeline."""
    llm = get_gemini_llm()
    if not llm:
        raise ValueError("Gemini LLM not initialized")
    
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)  
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    
    rag_chain = (
        {"context": retriever | format_docs, "query": RunnablePassthrough()}
        | prompt_template
        | llm
    )

    return rag_chain.invoke(query)

# =========================
# ENTRY POINT
# =========================

def main():
    print("Medical OCR Processor - Use streamlit_app.py to run the application")
    print(f"API Status - Gemini: {'✅' if GEMINI_API_KEY else '❌'}, Mistral: {'✅' if MISTRAL_API_KEY else '❌'}")

if __name__ == "__main__":
    main()
