# =========================
# IMPORT DEPENDENCIES
# =========================

import streamlit as st
import os
import tempfile
import base64
import shutil

# --- Import core RAG functions from medical_rag.py ---
from medical_rag import (
    process_medical_document, 
    create_vectorstore, 
    get_embedding_function,
    generate_response
)

# =========================
# SESSION STATE INITIALIZATION
# =========================

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'vectorstore' not in st.session_state:
        st.session_state.vectorstore = None

# =========================
# PDF PREVIEW FUNCTION
# =========================

def display_pdf(uploaded_file):
    """
    Display an uploaded PDF file inside the Streamlit interface.
    """
    # Read binary content of the PDF
    pdf_bytes = uploaded_file.getvalue()
    
    # Convert PDF to Base64 format
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # Create HTML iframe for displaying the PDF
    pdf_display = f"""
    <iframe 
        src="data:application/pdf;base64,{base64_pdf}" 
        width="700" 
        height="1000" 
        type="application/pdf"
        style="border: 1px solid #ddd; border-radius: 5px;"
    >
    </iframe>
    """
    
    # Render the PDF in Streamlit
    st.markdown(pdf_display, unsafe_allow_html=True)

# =========================
# MAIN STREAMLIT APPLICATION
# =========================

def main():
    """Main Streamlit application for Medical RAG Assistant."""
    
    # Page layout configuration
    st.set_page_config(
        page_title="Medical RAG Assistant",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Initialize session variables
    initialize_session_state()
    
    # Title and project description
    st.title("🩺 Medchat: AI for Medical Students")
    st.markdown("""
    **Medchat** is a specialized Data Science project designed to support medical students. 
    It serves as an intelligent Q&A tool and study aid, providing answers sourced **solely from verified medical textbooks** uploaded by the user. 
    Unlike generic AI, Medchat prioritizes accuracy and traceability to ensure reliable clinical information.
    """)
    
    # Create two-column layout
    col1, col2 = st.columns([1, 1])
    
    # =========================
    # LEFT PANEL: CONFIGURATION & DOCUMENT PROCESSING
    # =========================

    with col1:
        st.header("🔑 API Configuration")       
        
        # Input field for Gemini API Key
        gemini_key = st.text_input(
            "Gemini API Key:",
            type="password",
            placeholder="Enter your Gemini API key",
            help="Get your API key from https://aistudio.google.com/",
            key="gemini_key_input"
        )
        
        # Input field for Mistral API Key
        mistral_key = st.text_input(
            "Mistral API Key:",
            type="password", 
            placeholder="Enter your Mistral API key",
            help="Get your API key from https://console.mistral.ai/",
            key="mistral_key_input"
        )
        
        # Store API keys as environment variables at runtime
        if gemini_key: os.environ['GEMINI_API_KEY'] = gemini_key
        if mistral_key: os.environ['MISTRAL_API_KEY'] = mistral_key
        
        st.header("📁 Document Upload")
        
        # File uploader for medical PDF documents
        uploaded_file = st.file_uploader(
            "Choose a medical PDF file",
            type="pdf",
            help="Upload medical textbooks, research papers, or clinical guidelines."
        )

        # Button to trigger document processing
        process_clicked = st.button(
                "🚀 Process Document", 
                type="primary",
                use_container_width=True,
                key="process_btn"
            )
        
        # Execute document processing pipeline
        if uploaded_file and process_clicked:
            if not gemini_key or not mistral_key:
                st.error("Please enter both API keys.")
                return

            # Display document preview
            st.header("📄 Document Preview")
            display_pdf(uploaded_file)

            with st.spinner("Processing..."):
                # 1. Save uploaded file as a temporary PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # 2. Run OCR + text extraction + chunking pipeline
                try:
                    chunks = process_medical_document(tmp_path)
                    
                    if chunks:
                        # Create embedding function
                        emb_fn = get_embedding_function()
                        
                        # Use temporary storage for Chroma vector database
                        db_path = os.path.join(tempfile.gettempdir(), "medical_chroma_db")

                        # Remove old database to avoid conflicts
                        if os.path.exists(db_path):
                            shutil.rmtree(db_path)
                            print(f"🧹 Cleared old database at {db_path}")
                        
                        # Create vector store from chunks
                        vectorstore = create_vectorstore(chunks, emb_fn, db_path)
                        st.session_state.vectorstore = vectorstore
                        st.session_state.processing_complete = True
                        st.success(f"Processed {len(chunks)} chunks!")
                    else:
                        st.error("No text could be extracted.")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    # Remove temporary file after processing
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

    # =========================
    # RIGHT PANEL: MEDICAL Q&A INTERFACE
    # =========================

    with col2:
        st.header("💬 Medical Q&A")
        st.markdown("### 📚 Guidelines")
        st.markdown("""
        1. Enter Gemini API and Mistral OCR API.
        2. Upload your document and click "Process Document".
        3. Wait for the green **"Ready!"** message.
        4. Type your question on the right side.
        5. Read the answer and check the **"Sources"** to see the original text.
        """)

        # Only enable chat after document is processed
        if st.session_state.processing_complete:
            query = st.text_input("Ask a question:")
            
            if query and st.button("Ask"):
                with st.spinner("Thinking..."):
                    try:
                        # Generate RAG-based response
                        response = generate_response(query, st.session_state.vectorstore)
                        st.markdown(f"**Answer:** {response.content}")
                        
                        # Store conversation history
                        st.session_state.chat_history.append((query, response.content))
                    except Exception as e:
                        st.error(f"Generation Error: {e}")
            
            # Display chat history in expandable format
            for q, a in reversed(st.session_state.chat_history):
                with st.expander(f"Q: {q}"):
                    st.write(a)
        else:
            st.info("Upload and process a document to start chatting.")

# =========================
# APPLICATION ENTRY POINT
# =========================

if __name__ == "__main__":
    main()
