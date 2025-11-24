# # Import langchain modules
# from langchain_community.document_loaders import PyPDFLoader
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
# from langchain_community.vectorstores import Chroma
# from langchain_core.runnables import RunnablePassthrough
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.documents import Document
# from pydantic import BaseModel, Field
# import uuid

# # Import MistralOCR
# from mistralai import Mistral
# from mistralai import DocumentURLChunk, ImageURLChunk
# from mistralai.models import OCRResponse

# # Other modules and packages
# import os
# import io
# import base64
# import tempfile
# from PIL import Image
# import streamlit as st
# import pandas as pd
# from dotenv import find_dotenv, load_dotenv
# import hashlib

# # Load Gemini API and Mistral OCR
# load_dotenv()
# MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# # Set the configure
# mistral_client = Mistral(api_key=MISTRAL_API_KEY)  
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7, google_api_key = GEMINI_API_KEY)

# # Prompt template
# PROMPT_TEMPLATE = """
#  You are an assistant for question-answering tasks.
# Use the following pieces of retrieved context to answer the question. 
# If you don't know the answer, say that you don't know. DON'T MAKE UP ANYTHING.

# {context}

# ---

# Answer the question based on the above context: {question}
# """

# def upload_pdf(client, content, filename):
#     if client is None:
#         raise ValueError("Mistral client is not initialized")
    
#     with tempfile.TemporaryDirectory() as temp_dir:
#         temp_path = os.path.join(temp_dir, filename)

#         with open(temp_path, "wb") as tmp:
#             tmp.write(content)
#         try:
#             with open(temp_path, "rb") as file_obj:
#                 file_upload = client.files.upload(
#                     file = {"file_name": filename, "content": file_obj}
#                 )
#                 signed_url = client.files.get_signed_url(file_id = file_upload.id)
#                 return signed_url.url
#         except Exception as e:
#             raise ValueError(f"Error uploading PDF: {str(e)}")
#         finally:
#             if os.path.exists(temp_path):
#                 os.remove(temp_path)

# def load_and_chunk(path):
#     loader = PyPDFLoader(path)
#     pages = loader.load()

#     # Split document
#     # text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500,
#     #                                            chunk_overlap=200,
#     #                                            length_function=len,
#     #                                            separators=["\n\n", "\n", " "])

#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,
#                                                chunk_overlap=200,
#                                                length_function=len)
    
#     chunks = text_splitter.split_documents(pages)
#     return chunks

# def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
#     for img_name, base64_str in images_dict.items():
#         markdown_str = markdown_str.replace(f"[{img_name}({img_name})]", f":[{img_name}({base64_str})]")
    
#     return markdown_str

# def get_combined_markdown(ocr_response: OCRResponse) -> str:
#     markdowns: list[str] = []

#     for page in ocr_response.pages:
#         image_data = {}
#         for img in page.images:
#             image_data[img.id] = img.image_base64
#         markdowns.append(replace_images_in_markdown(page.markdown, image_data))
#     return "\n\n".join(markdowns)

# def process_ocr(client, document_source):
#     if client is None:
#         raise ValueError("Mistral client is not initialized")
    
#     if document_source["type"] == "document_url":
#         return client.ocr.process(
#             document = DocumentURLChunk(document_url = document_source["document_url"]),
#             model = "mistral-ocr-latest",
#             include_image_base64 = True
#         )
    
#     elif document_source["type"] == "image_url":
#         return client.ocr.process(
#             document = ImageURLChunk(image_url = document_source["image_url"]),
#             model = "mistral-ocr-latest",
#             include_image_base64 = True
#         )
    
#     else:
#         raise ValueError(f"Unsupported document source type: {document_source['type']}")
    
# def process_with_ocr(file_path):
#     """Process document with Mistral OCR"""
#     try:
#         # Upload and get signed URL
#         with open(file_path, "rb") as f:
#             content = f.read()
        
#         signed_url = upload_pdf(mistral_client, content, os.path.basename(file_path))
        
#         # Process OCR
#         ocr_response = process_ocr(
#             mistral_client, 
#             {"type": "document_url", "document_url": signed_url}
#         )
        
#         # Convert to markdown and chunk
#         combined_md = get_combined_markdown(ocr_response)
        
#         # Create document from OCR result
#         ocr_doc = Document(
#             page_content=combined_md,
#             metadata={"source": file_path, "processing_method": "ocr"}
#         )
        
#         # Chunk the OCR result
#         text_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=1000,
#             chunk_overlap=100
#         )
        
#         return text_splitter.split_documents([ocr_doc])
        
#     except Exception as e:
#         print(f"OCR processing failed: {e}")
#         return []

# def process_medical_document(file_path):
#     """Main processing pipeline for medical documents"""
#     all_chunks = []

#     # Processing for documents
#     text_chunks = load_and_chunk(file_path)
#     all_chunks.extend(text_chunks)
#     # OCR processing
#     try:
#         ocr_chunks = process_with_ocr(file_path)
#         all_chunks.extend(ocr_chunks)

#     except Exception as e:
#         print(f"OCR processing failed")

#     # Add medical_specific metada
#     for chunk in all_chunks:
#         chunk.metadata.update({
#             "document_type": "medical",
#             "processed_with": "gemini_mistral",
#             "chunk_id": hashlib.md5(chunk.page_content.encode()).hexdigest()[:8]
#         })
    
#     return all_chunks


# def format_docs(docs):
#     return "\n\n --- \n\n".join([doc.page_content for doc in docs])

# def get_embedding_function():
#     embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", 
#                                               google_api_key=GEMINI_API_KEY,
#                                               output_dimensionality = 1536)
#     return embeddings

# def create_vectorstore(chunks, embedding_function, vectorstore_path):
#     # Create a list of unique ids for each document based on the content
#     ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, doc.page_content)) for doc in chunks]

#     # Ensure that only unique docs with unique ids are kept
#     unique_ids = set()
#     unique_chunks = []

#     for chunk, id in zip(chunks, ids):
#         if id not in unique_ids:
#             unique_ids.add(id)
#             unique_chunks.append(chunk)

#     # Create new new Chroma database from teh documents
#     vectorstore = Chroma.from_documents(documents=chunks,
#                                         embedding = embedding_function,
#                                         persist_directory=vectorstore_path)
#     vectorstore.persist()
#     return vectorstore

# def generate_response(query, vectorstore):  
#     """Generate response using RAG chain"""
#     prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)  

#     # Create retriever 
#     retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
#     rag_chain = (
#         {"context": retriever | format_docs, "question": RunnablePassthrough()}
#         | prompt_template
#         | llm
#     )

#     response = rag_chain.invoke(query)
#     return response

# def main():
#     print("Medical OCR Processor - Use streamlit_app.py to run the application")

# if __name__ == "__main__":
#     main()


# Import langchain modules
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from pydantic import BaseModel, Field
import uuid

# Import MistralOCR
from mistralai import Mistral
from mistralai import DocumentURLChunk, ImageURLChunk
from mistralai.models import OCRResponse

# Other modules and packages
import os
import io
import base64
import tempfile
from PIL import Image
import streamlit as st
import pandas as pd
from dotenv import find_dotenv, load_dotenv
import hashlib
import time
import json
from datetime import datetime

# Load Gemini API and Mistral OCR
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Rate limit tracking
class RateLimitTracker:
    def __init__(self):
        self.requests_made = 0
        self.last_reset = time.time()
        self.max_requests_per_minute = 20  # Mistral free tier limit
        
    def check_rate_limit(self):
        current_time = time.time()
        if current_time - self.last_reset >= 60:  # Reset every minute
            self.requests_made = 0
            self.last_reset = current_time
            
        if self.requests_made >= self.max_requests_per_minute:
            wait_time = 60 - (current_time - self.last_reset)
            print(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
            self.requests_made = 0
            self.last_reset = time.time()
            
        self.requests_made += 1
        return self.requests_made, self.max_requests_per_minute

rate_tracker = RateLimitTracker()

# Initialize clients with error handling
try:
    mistral_client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None
    print(f"✅ Mistral client initialized")
except Exception as e:
    print(f"❌ Error initializing Mistral client: {e}")
    mistral_client = None

try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7, google_api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
    print(f"✅ Gemini client initialized")
except Exception as e:
    print(f"❌ Error initializing Gemini client: {e}")
    llm = None

# Prompt template
PROMPT_TEMPLATE = """
You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, say that you don't know. DON'T MAKE UP ANYTHING.

{context}

---

Answer the question based on the above context: {query}
"""

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
    current, max_limit = rate_tracker.check_rate_limit()
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

def diagnose_pdf_issue(file_path):
    """Run comprehensive diagnostics on PDF file"""
    print("\n" + "🔍"*20)
    print("PDF FILE DIAGNOSTICS")
    print("🔍"*20)
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Basic file info
        file_size = len(content)
        print(f"File size: {file_size} bytes ({file_size/1024:.1f}KB)")
        
        # Check PDF header
        header = content[:10]
        print(f"PDF header: {header}")
        
        # Check if it starts with %PDF
        if content[:4] == b'%PDF':
            print("✅ Valid PDF header found")
            
            # Try to get PDF version
            version_line = content[:20].decode('ascii', errors='ignore')
            print(f"PDF version info: {version_line}")
        else:
            print("❌ Invalid PDF header - file may be corrupted")
            
        # Check for common PDF structures
        if b'obj' in content[:1000] and b'endobj' in content[:1000]:
            print("✅ PDF structure appears valid")
        else:
            print("⚠️  PDF structure may be unusual")
            
        # Try to read with PyPDF to validate
        try:
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            print(f"✅ PyPDFLoader can read file: {len(pages)} pages")
        except Exception as e:
            print(f"❌ PyPDFLoader cannot read file: {e}")
            
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
    
    print("🔍"*20 + "\n")

def upload_pdf(client, content, filename):
    if client is None:
        raise ValueError("Mistral client is not initialized")
    
    # Print comprehensive metrics before upload
    print_api_metrics(client)
    
    # Enhanced file validation
    file_size = len(content)
    file_size_mb = file_size / (1024 * 1024)
    
    print(f"🔍 File Validation:")
    print(f"   File name: {filename}")
    print(f"   File size: {file_size} bytes ({file_size_mb:.2f}MB)")
    print(f"   Within 10MB limit: {'✅' if file_size_mb <= 10 else '❌'}")
    
    if file_size_mb > 10:
        raise ValueError(f"File too large: {file_size_mb:.2f}MB. Mistral OCR limit is 10MB.")
    
    # Check if file is a valid PDF
    if not filename.lower().endswith('.pdf'):
        raise ValueError(f"Invalid file format: {filename}. Only PDF files are supported.")
    
    # Check PDF header magic bytes
    pdf_header = content[:4]
    if pdf_header != b'%PDF':
        print(f"⚠️  Warning: File may not be a valid PDF. Header: {pdf_header}")
    
    # Check rate limit
    current, max_limit = rate_tracker.check_rate_limit()
    print(f"📤 API Request {current}/{max_limit} - Uploading PDF")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_path = temp_file.name
        temp_file.write(content)
    
    try:
        with open(temp_path, "rb") as file_obj:
            print(f"🔄 Starting file upload to Mistral...")
            
            # Try to upload with detailed error handling
            try:
                file_upload = client.files.upload(
                    file={"file_name": filename, "content": file_obj}
                )
                print(f"✅ File uploaded successfully. File ID: {file_upload.id}")
                
                # Get signed URL
                signed_url = client.files.get_signed_url(file_id=file_upload.id)
                print(f"✅ Signed URL obtained")
                
                return signed_url.url
                
            except Exception as upload_error:
                error_str = str(upload_error)
                print(f"❌ Upload failed with error: {error_str}")
                
                # Analyze common error patterns
                if "422" in error_str:
                    print(f"🔍 422 Error Analysis:")
                    print(f"   - Usually indicates file format issues")
                    print(f"   - File may be corrupted or non-standard PDF")
                    print(f"   - Try re-saving the PDF with a different tool")
                elif "413" in error_str:
                    print(f"🔍 413 Error: File too large")
                elif "429" in error_str:
                    print(f"🔍 429 Error: Rate limit exceeded")
                elif "401" in error_str:
                    print(f"🔍 401 Error: Invalid API key")
                else:
                    print(f"🔍 Unknown error type")
                
                raise upload_error
                
    except Exception as e:
        raise ValueError(f"Error uploading PDF: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def load_and_chunk(path):
    loader = PyPDFLoader(path)
    pages = loader.load()

    # Split document
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " "]
    )
    
    chunks = text_splitter.split_documents(pages)
    return chunks

def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(f"[{img_name}({img_name})]", f":[{img_name}({base64_str})]")
    
    return markdown_str

def get_combined_markdown(ocr_response: OCRResponse) -> str:
    markdowns: list[str] = []

    for page in ocr_response.pages:
        image_data = {}
        for img in page.images:
            image_data[img.id] = img.image_base64
        markdowns.append(replace_images_in_markdown(page.markdown, image_data))
    return "\n\n".join(markdowns)

def process_ocr(client, document_source):
    if client is None:
        raise ValueError("Mistral client is not initialized")
    
    # Check rate limit
    current, max_limit = rate_tracker.check_rate_limit()
    print(f"🔍 API Request {current}/{max_limit} - Processing OCR")
    
    if document_source["type"] == "document_url":
        return client.ocr.process(
            document=DocumentURLChunk(document_url=document_source["document_url"]),
            model="mistral-ocr-latest",
            include_image_base64=True
        )
    
    elif document_source["type"] == "image_url":
        return client.ocr.process(
            document=ImageURLChunk(image_url=document_source["image_url"]),
            model="mistral-ocr-latest",
            include_image_base64=True
        )
    
    else:
        raise ValueError(f"Unsupported document source type: {document_source['type']}")
    
def process_with_ocr(file_path):
    """Process document with Mistral OCR"""
    try:
        # Upload and get signed URL
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Print metrics before processing
        print_api_metrics(mistral_client, file_path)
        
        file_size_mb = len(content) / (1024 * 1024)
        print(f"🔄 Processing file: {os.path.basename(file_path)} ({file_size_mb:.2f}MB)")
        
        if file_size_mb > 10:
            print(f"⚠️  Warning: File size ({file_size_mb:.2f}MB) exceeds recommended 10MB limit")
            return []
        
        signed_url = upload_pdf(mistral_client, content, os.path.basename(file_path))
        
        # Process OCR with metrics
        current, max_limit = rate_tracker.check_rate_limit()
        print(f"🔍 API Request {current}/{max_limit} - Starting OCR processing")
        
        ocr_response = process_ocr(
            mistral_client, 
            {"type": "document_url", "document_url": signed_url}
        )
        
        print(f"✅ OCR processing completed successfully")
        print(f"   Pages processed: {len(ocr_response.pages)}")
        
        # Convert to markdown and chunk
        combined_md = get_combined_markdown(ocr_response)
        
        # Create document from OCR result
        ocr_doc = Document(
            page_content=combined_md,
            metadata={"source": file_path, "processing_method": "ocr"}
        )
        
        # Chunk the OCR result
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        
        ocr_chunks = text_splitter.split_documents([ocr_doc])
        print(f"✅ Created {len(ocr_chunks)} OCR chunks")
        
        return ocr_chunks
        
    except Exception as e:
        print(f"❌ OCR processing failed: {e}")
        
        # Print final metrics after failure
        current, max_limit = rate_tracker.check_rate_limit()
        print(f"📊 Final API metrics:")
        print(f"   Requests made this minute: {current}/{max_limit}")
        print(f"   Remaining requests: {max_limit - current}")
        
        return []

def process_medical_document(file_path):
    """Main processing pipeline for medical documents"""
    all_chunks = []

    # Print file info
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
    print(f"📄 Processing document: {os.path.basename(file_path)} ({file_size:.2f}MB)")
    
    # Run PDF diagnostics
    diagnose_pdf_issue(file_path)
    
    # Regular text processing
    print("📖 Extracting text from PDF...")
    text_chunks = load_and_chunk(file_path)
    all_chunks.extend(text_chunks)
    print(f"✅ Extracted {len(text_chunks)} text chunks")
    
    # OCR processing only for files under 10MB and after diagnostics
    if file_size < 10 and mistral_client is not None:
        print("🔍 Running OCR for images and tables...")
        try:
            ocr_chunks = process_with_ocr(file_path)
            all_chunks.extend(ocr_chunks)
            print(f"✅ Added {len(ocr_chunks)} OCR chunks")
        except Exception as e:
            print(f"❌ OCR processing failed: {e}")
    else:
        if file_size >= 10:
            print(f"⚠️  Skipping OCR - file too large ({file_size:.2f}MB > 10MB limit)")
        else:
            print("⚠️  Skipping OCR - Mistral client not available")
    
    # Add medical-specific metadata
    for chunk in all_chunks:
        chunk.metadata.update({
            "document_type": "medical",
            "processed_with": "gemini_mistral",
            "chunk_id": hashlib.md5(chunk.page_content.encode()).hexdigest()[:8]
        })
    
    print(f"🎯 Total chunks processed: {len(all_chunks)}")
    return all_chunks

def format_docs(docs):
    return "\n\n --- \n\n".join([doc.page_content for doc in docs])

def get_embedding_function():
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key not configured")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001", 
        google_api_key=GEMINI_API_KEY
    )
    return embeddings

def create_vectorstore(chunks, embedding_function, vectorstore_path):
    if not chunks:
        raise ValueError("No chunks provided for vector store creation")
    
    # Create a list of unique ids for each document based on the content
    ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, doc.page_content)) for doc in chunks]

    # Ensure that only unique docs with unique ids are kept
    unique_ids = set()
    unique_chunks = []

    for chunk, id in zip(chunks, ids):
        if id not in unique_ids:
            unique_ids.add(id)
            unique_chunks.append(chunk)

    print(f"🔧 Creating vector store with {len(unique_chunks)} unique chunks...")
    
    # Create new Chroma database from the documents
    vectorstore = Chroma.from_documents(
        documents=unique_chunks,
        embedding=embedding_function,
        persist_directory=vectorstore_path
    )
    vectorstore.persist()
    print("✅ Vector store created successfully")
    return vectorstore

def generate_response(query, vectorstore):  
    """Generate response using RAG chain"""
    if not llm:
        raise ValueError("Gemini LLM not initialized")
    
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)  

    # Create retriever 
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt_template
        | llm
    )

    response = rag_chain.invoke(query)
    return response

def main():
    print("Medical OCR Processor - Use streamlit_app.py to run the application")
    print(f"API Status - Gemini: {'✅' if GEMINI_API_KEY else '❌'}, Mistral: {'✅' if MISTRAL_API_KEY else '❌'}")

if __name__ == "__main__":
    main()