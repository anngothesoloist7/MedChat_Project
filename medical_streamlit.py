import streamlit as st
import os
import tempfile
import base64
import shutil

# --- Funtions from medical_rag.py ----
from medical_rag import (
    process_medical_document, 
    create_vectorstore, 
    get_embedding_function,
    generate_response
)

def initialize_session_state():
    """Initialize session state variables"""
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'vectorstore' not in st.session_state:
        st.session_state.vectorstore = None

def display_pdf(uploaded_file):
    """
    Display a PDF file that has been uploaded to Streamlit.
    """
    # Read the PDF file
    pdf_bytes = uploaded_file.getvalue()
    
    # Convert to base64
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # Create PDF display HTML
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
    
    # Display the PDF
    st.markdown(pdf_display, unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    # Page configuration
    st.set_page_config(
        page_title="Medical RAG Assistant",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Initialize session state
    initialize_session_state()
    
    st.title("🩺 Medchat: AI for Medical Students")
    st.markdown("""
    **Medchat** is a specialized Data Science project designed to support medical students. 
    It serves as an intelligent Q&A tool and study aid, providing answers sourced **solely from verified medical textbooks** uploaded by the user. 
    Unlike generic AI, Medchat prioritizes accuracy and traceability to ensure reliable clinical information.
    """)
    
    # Create two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("🔑 API Configuration")       
        
        # API key input
        gemini_key = st.text_input(
            "Gemini API Key:",
            type="password",
            placeholder="Enter your Gemini API key",
            help="Get your API key from https://aistudio.google.com/",
            key="gemini_key_input"
        )
        
        mistral_key = st.text_input(
            "Mistral API Key:",
            type="password", 
            placeholder="Enter your Mistral API key",
            help="Get your API key from https://console.mistral.ai/",
            key="mistral_key_input"
        )
        
       # Set Environment Variables Immediately
        if gemini_key: os.environ['GEMINI_API_KEY'] = gemini_key
        if mistral_key: os.environ['MISTRAL_API_KEY'] = mistral_key
        
        st.header("📁 Document Upload")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a medical PDF file",
            type="pdf",
            help="Upload medical textbooks, research papers, or clinical guidelines."
        )

        process_clicked = st.button(
                "🚀 Process Document", 
                type="primary",
                use_container_width=True,
                key="process_btn"
            )
        
        if uploaded_file and process_clicked:
            if not gemini_key or not mistral_key:
                st.error("Please enter both API keys.")
                return

            st.header("📄 Document Preview")
            display_pdf(uploaded_file)

            with st.spinner("Processing..."):
                # 1. Create Temp File
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # 2. Process (File is closed now, safe to use)
                try:
                    chunks = process_medical_document(tmp_path)
                    
                    if chunks:
                        # Create Vector Store
                        emb_fn = get_embedding_function()
                        # Use a temp dir for Chroma to avoid locks
                        db_path = os.path.join(tempfile.gettempdir(), "medical_chroma_db")

                        if os.path.exists(db_path):
                            shutil.rmtree(db_path)
                            print(f"🧹 Cleared old database at {db_path}")
                        
                        vectorstore = create_vectorstore(chunks, emb_fn, db_path)
                        st.session_state.vectorstore = vectorstore
                        st.session_state.processing_complete = True
                        st.success(f"Processed {len(chunks)} chunks!")
                    else:
                        st.error("No text could be extracted.")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    # Cleanup
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

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

        if st.session_state.processing_complete:
            query = st.text_input("Ask a question:")
            if query and st.button("Ask"):
                with st.spinner("Thinking..."):
                    try:
                        response = generate_response(query, st.session_state.vectorstore)
                        st.markdown(f"**Answer:** {response.content}")
                        
                        # Save to history
                        st.session_state.chat_history.append((query, response.content))
                    except Exception as e:
                        st.error(f"Generation Error: {e}")
            
            # Show History
            for q, a in reversed(st.session_state.chat_history):
                with st.expander(f"Q: {q}"):
                    st.write(a)
        else:
            st.info("Upload and process a document to start chatting.")
        
    
    # # Show PDF preview and chat interface if processing is complete
    # if st.session_state.processing_complete and uploaded_file is not None:
    #     st.header("📄 Document Preview")
    #     display_pdf(uploaded_file)
        
    #     # Display chat interface
    #     st.header("💬 Medical Q&A")
        
    #     # Display chat history
    #     if st.session_state.chat_history:
    #         for i, (question, answer, sources) in enumerate(st.session_state.chat_history):
    #             with st.expander(f"Q: {question[:80]}...", expanded=(i == len(st.session_state.chat_history)-1)):
    #                 st.markdown(f"**❓ Question:** {question}")
    #                 st.markdown(f"**🎯 Answer:** {answer}")
                    
    #                 # Display sources
    #                 if sources and len(sources) > 0:
    #                     with st.expander("📚 Reference Sources"):
    #                         for j, source in enumerate(sources):
    #                             st.markdown(f"**Source {j+1}:**")
    #                             st.text(source[:400] + "..." if len(source) > 400 else source)
    #                             st.divider()
    #     else:
    #         st.info("💡 Ask a question about the medical document to get started!")
        
    #     # Question input
    #     st.divider()
    #     col1, col2 = st.columns([4, 1])
        
    #     with col1:
    #         question = st.text_input(
    #             "Ask a medical question:",
    #             placeholder="e.g., What are the clinical features and management of acute myocardial infarction?",
    #             key="question_input",
    #             label_visibility="collapsed"
    #         )
        
    #     with col2:
    #         st.write("")  # Spacing
    #         st.write("")
    #         ask_button = st.button("Ask", type="primary", use_container_width=True, key="ask_btn")
        
    #     if ask_button and question:
    #         with st.spinner("🔍 Searching medical knowledge..."):
    #             try:
    #                 # Generate response
    #                 response = generate_response(question, st.session_state.vectorstore)
                    
    #                 # Retrieve sources for display
    #                 retriever = st.session_state.vectorstore.as_retriever(
    #                     search_type="similarity",
    #                     search_kwargs={"k": 3}
    #                 )
                    
    #                 # Use the new invoke method
    #                 relevant_docs = retriever.invoke(question)
    #                 sources = [doc.page_content for doc in relevant_docs]
                    
    #                 # Add to chat history
    #                 st.session_state.chat_history.append(
    #                     (question, response.content, sources)
    #                 )
                    
    #                 # Rerun to update display
    #                 st.rerun()
                    
    #             except Exception as e:
    #                 st.error(f"❌ Error generating response: {str(e)}")
        
    #     # Document info sidebar
    #     st.sidebar.header("📊 Document Info")
    #     st.sidebar.success(f"✅ **Loaded:** {st.session_state.document_name}")
    #     st.sidebar.info(f"📚 **Knowledge Chunks:** {len(st.session_state.processed_docs)}")
        
    #     # Clear conversation button
    #     if st.sidebar.button("🗑️ Clear Conversation", key="clear_chat"):
    #         st.session_state.chat_history = []
    #         st.rerun()
        
    #     # Show chat statistics
    #     if st.session_state.chat_history:
    #         st.sidebar.divider()
    #         st.sidebar.metric("💬 Questions Asked", len(st.session_state.chat_history))


if __name__ == "__main__":
    main()