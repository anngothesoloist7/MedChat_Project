# import streamlit as st
# import os
# import tempfile
# import base64
# from medical_rag import (
#     process_medical_document, 
#     create_vectorstore, 
#     get_embedding_function,
#     generate_response
# )

# def initialize_session_state():
#     """Initialize session state variables"""
#     if 'vectorstore' not in st.session_state:
#         st.session_state.vectorstore = None
#     if 'processed_docs' not in st.session_state:
#         st.session_state.processed_docs = []
#     if 'document_name' not in st.session_state:
#         st.session_state.document_name = None
#     if 'chat_history' not in st.session_state:
#         st.session_state.chat_history = []
#     if 'processing_complete' not in st.session_state:
#         st.session_state.processing_complete = False

# def display_pdf(uploaded_file):
#     """
#     Display a PDF file that has been uploaded to Streamlit.
#     """
#     # Read the PDF file
#     pdf_bytes = uploaded_file.getvalue()
    
#     # Convert to base64
#     base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
#     # Create PDF display HTML
#     pdf_display = f"""
#     <iframe 
#         src="data:application/pdf;base64,{base64_pdf}" 
#         width="700" 
#         height="1000" 
#         type="application/pdf"
#         style="border: 1px solid #ddd; border-radius: 5px;"
#     >
#     </iframe>
#     """
    
#     # Display the PDF
#     st.markdown(pdf_display, unsafe_allow_html=True)

# def main():
#     """Main Streamlit application"""
#     # Page configuration
#     st.set_page_config(
#         page_title="Medical RAG Assistant",
#         page_icon="🩺",
#         layout="wide",
#         initial_sidebar_state="collapsed"
#     )
    
#     # Initialize session state
#     initialize_session_state()
    
#     st.title("🩺 Medical RAG Assistant")
    
#     # Create two columns
#     col1, col2 = st.columns([1, 1])
    
#     with col1:
#         st.header("🔑 API Configuration")
        
#         # API key input
#         gemini_api_key = st.text_input(
#             "Gemini API Key:",
#             type="password",
#             placeholder="Enter your Gemini API key",
#             help="Get your API key from https://aistudio.google.com/",
#             key="gemini_key_input"
#         )
        
#         mistral_api_key = st.text_input(
#             "Mistral API Key:",
#             type="password", 
#             placeholder="Enter your Mistral API key",
#             help="Get your API key from https://console.mistral.ai/",
#             key="mistral_key_input"
#         )
        
#         # Store API keys in session state
#         if gemini_api_key:
#             st.session_state.gemini_api_key = gemini_api_key
#             os.environ['GEMINI_API_KEY'] = gemini_api_key
        
#         if mistral_api_key:
#             st.session_state.mistral_api_key = mistral_api_key
#             os.environ['MISTRAL_API_KEY'] = mistral_api_key
        
#         st.header("📁 Document Upload")
        
#         # File uploader
#         uploaded_file = st.file_uploader(
#             "Choose a medical PDF file",
#             type="pdf",
#             help="Upload medical textbooks, research papers, or clinical guidelines"
#         )
        
#         # Process document button
#         process_clicked = False
#         if uploaded_file is not None:
#             st.success(f"✅ File uploaded: {uploaded_file.name}")
#             process_clicked = st.button(
#                 "🚀 Process Document", 
#                 type="primary",
#                 use_container_width=True,
#                 key="process_btn"
#             )
    
#     with col2:
#         st.header("🩺 Medical RAG Assistant")
#         st.markdown("""
#         ### Welcome to Your Medical Learning Companion!
        
#         **How to use:**
#         1. 🔑 Enter BOTH API keys (Gemini & Mistral)
#         2. 📁 Upload a medical PDF document  
#         3. 🚀 Click 'Process Document' to analyze content
#         4. 💬 Ask medical questions in the chat
        
#         **Current Status:**
#         """)
        
#         # Display API status
#         gemini_configured = hasattr(st.session_state, 'gemini_api_key') and st.session_state.gemini_api_key
#         mistral_configured = hasattr(st.session_state, 'mistral_api_key') and st.session_state.mistral_api_key
        
#         if gemini_configured:
#             st.success("✅ Gemini API: Configured")
#         else:
#             st.error("❌ Gemini API: Not configured")
            
#         if mistral_configured:
#             st.success("✅ Mistral API: Configured")
#         else:
#             st.error("❌ Mistral API: Not configured")
            
#         # Display processing status
#         if st.session_state.processing_complete:
#             st.success("✅ Document Processing: Complete")
#         elif uploaded_file and not st.session_state.processing_complete:
#             st.info("📄 Document Ready for Processing")
#         else:
#             st.info("⏳ Waiting for document upload...")
    
#     # Process document if uploaded and button clicked
#     if uploaded_file is not None and process_clicked:
#         # Check if API keys are configured
#         if not hasattr(st.session_state, 'gemini_api_key') or not st.session_state.gemini_api_key:
#             st.error("❌ Please enter your Gemini API key to proceed")
#         elif not hasattr(st.session_state, 'mistral_api_key') or not st.session_state.mistral_api_key:
#             st.error("❌ Please enter your Mistral API key to proceed")
#         else:
#             with st.spinner("🔄 Processing medical document... This may take a few minutes."):
#                 # Save uploaded file temporarily
#                 with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
#                     tmp_file.write(uploaded_file.getvalue())
#                     tmp_path = tmp_file.name
                
#                 try:
#                     # Process document
#                     chunks = process_medical_document(tmp_path)
#                     st.session_state.processed_docs = chunks
#                     st.session_state.document_name = uploaded_file.name
                    
#                     # Create vector store
#                     embedding_function = get_embedding_function()
#                     vectorstore = create_vectorstore(
#                         chunks=chunks,
#                         embedding_function=embedding_function,
#                         vectorstore_path="./medical_vectorstore"
#                     )
#                     st.session_state.vectorstore = vectorstore
#                     st.session_state.processing_complete = True
                    
#                     st.success(f"✅ Successfully processed {len(chunks)} knowledge chunks from {uploaded_file.name}")
                    
#                 except Exception as e:
#                     st.error(f"❌ Error processing document: {str(e)}")
#                 finally:
#                     # Clean up temp file
#                     if os.path.exists(tmp_path):
#                         os.unlink(tmp_path)
    
#     # Show PDF preview and chat interface if processing is complete
#     if st.session_state.processing_complete and uploaded_file is not None:
#         st.header("📄 Document Preview")
#         display_pdf(uploaded_file)
        
#         # Display chat interface
#         st.header("💬 Medical Q&A")
        
#         # Display chat history
#         if st.session_state.chat_history:
#             for i, (question, answer, sources) in enumerate(st.session_state.chat_history):
#                 with st.expander(f"Q: {question[:80]}...", expanded=(i == len(st.session_state.chat_history)-1)):
#                     st.markdown(f"**❓ Question:** {question}")
#                     st.markdown(f"**🎯 Answer:** {answer}")
                    
#                     # Display sources
#                     if sources and len(sources) > 0:
#                         with st.expander("📚 Reference Sources"):
#                             for j, source in enumerate(sources):
#                                 st.markdown(f"**Source {j+1}:**")
#                                 st.text(source[:400] + "..." if len(source) > 400 else source)
#                                 st.divider()
#         else:
#             st.info("💡 Ask a question about the medical document to get started!")
        
#         # Question input
#         st.divider()
#         col1, col2 = st.columns([4, 1])
        
#         with col1:
#             question = st.text_input(
#                 "Ask a medical question:",
#                 placeholder="e.g., What are the clinical features and management of acute myocardial infarction?",
#                 key="question_input",
#                 label_visibility="collapsed"
#             )
        
#         with col2:
#             st.write("")  # Spacing
#             st.write("")
#             ask_button = st.button("Ask", type="primary", use_container_width=True, key="ask_btn")
        
#         if ask_button and question:
#             with st.spinner("🔍 Searching medical knowledge..."):
#                 try:
#                     # Generate response
#                     response = generate_response(question, st.session_state.vectorstore)
                    
#                     # Retrieve sources for display
#                     retriever = st.session_state.vectorstore.as_retriever(
#                         search_type="similarity",
#                         search_kwargs={"k": 3}
#                     )
#                     relevant_docs = retriever.invoke(question)
#                     sources = [doc.page_content for doc in relevant_docs]
                    
#                     # Add to chat history
#                     st.session_state.chat_history.append(
#                         (question, response.content, sources)
#                     )
                    
#                     # Rerun to update display
#                     st.rerun()
                    
#                 except Exception as e:
#                     st.error(f"❌ Error generating response: {str(e)}")
        
#         # Document info sidebar
#         st.sidebar.header("📊 Document Info")
#         st.sidebar.success(f"✅ **Loaded:** {st.session_state.document_name}")
#         st.sidebar.info(f"📚 **Knowledge Chunks:** {len(st.session_state.processed_docs)}")
        
#         # Clear conversation button
#         if st.sidebar.button("🗑️ Clear Conversation", key="clear_chat"):
#             st.session_state.chat_history = []
#             st.rerun()
        
#         # Show chat statistics
#         if st.session_state.chat_history:
#             st.sidebar.divider()
#             st.sidebar.metric("💬 Questions Asked", len(st.session_state.chat_history))

# if __name__ == "__main__":
#     main()


import streamlit as st
import os
import tempfile
import base64
from medical_rag import (
    process_medical_document, 
    create_vectorstore, 
    get_embedding_function,
    generate_response
)

def initialize_session_state():
    """Initialize session state variables"""
    if 'vectorstore' not in st.session_state:
        st.session_state.vectorstore = None
    if 'processed_docs' not in st.session_state:
        st.session_state.processed_docs = []
    if 'document_name' not in st.session_state:
        st.session_state.document_name = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'processing_error' not in st.session_state:
        st.session_state.processing_error = None

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
    
    st.title("🩺 Medical RAG Assistant")
    
    # Create two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("🔑 API Configuration")
        
        # API key input
        gemini_api_key = st.text_input(
            "Gemini API Key:",
            type="password",
            placeholder="Enter your Gemini API key",
            help="Get your API key from https://aistudio.google.com/",
            key="gemini_key_input"
        )
        
        mistral_api_key = st.text_input(
            "Mistral API Key:",
            type="password", 
            placeholder="Enter your Mistral API key",
            help="Get your API key from https://console.mistral.ai/",
            key="mistral_key_input"
        )
        
        # Store API keys in session state
        if gemini_api_key:
            st.session_state.gemini_api_key = gemini_api_key
            os.environ['GEMINI_API_KEY'] = gemini_api_key
        
        if mistral_api_key:
            st.session_state.mistral_api_key = mistral_api_key
            os.environ['MISTRAL_API_KEY'] = mistral_api_key
        
        st.header("📁 Document Upload")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a medical PDF file",
            type="pdf",
            help="Upload medical textbooks, research papers, or clinical guidelines. Max recommended: 10MB"
        )
        
        # Process document button
        process_clicked = False
        if uploaded_file is not None:
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.info(f"📄 File: {uploaded_file.name} ({file_size_mb:.2f}MB)")
            
            if file_size_mb > 10:
                st.warning("⚠️ Large file detected. OCR processing may fail. Consider using a smaller file.")
            
            process_clicked = st.button(
                "🚀 Process Document", 
                type="primary",
                use_container_width=True,
                key="process_btn"
            )
    
    with col2:
        st.header("🩺 Medical RAG Assistant")
        st.markdown("""
        ### Welcome to Your Medical Learning Companion!
        
        **How to use:**
        1. 🔑 Enter BOTH API keys (Gemini & Mistral)
        2. 📁 Upload a medical PDF document  
        3. 🚀 Click 'Process Document' to analyze content
        4. 💬 Ask medical questions in the chat
        
        **Current Status:**
        """)
        
        # Display API status
        gemini_configured = hasattr(st.session_state, 'gemini_api_key') and st.session_state.gemini_api_key
        mistral_configured = hasattr(st.session_state, 'mistral_api_key') and st.session_state.mistral_api_key
        
        if gemini_configured:
            st.success("✅ Gemini API: Configured")
        else:
            st.error("❌ Gemini API: Not configured")
            
        if mistral_configured:
            st.success("✅ Mistral API: Configured")
        else:
            st.error("❌ Mistral API: Not configured")
            
        # Display processing status
        if st.session_state.processing_complete:
            st.success("✅ Document Processing: Complete")
        elif st.session_state.processing_error:
            st.error(f"❌ Processing Error: {st.session_state.processing_error}")
        elif uploaded_file and not st.session_state.processing_complete:
            st.info("📄 Document Ready for Processing")
        else:
            st.info("⏳ Waiting for document upload...")
    
    # Process document if uploaded and button clicked
    if uploaded_file is not None and process_clicked:
        # Check if API keys are configured
        if not hasattr(st.session_state, 'gemini_api_key') or not st.session_state.gemini_api_key:
            st.error("❌ Please enter your Gemini API key to proceed")
        elif not hasattr(st.session_state, 'mistral_api_key') or not st.session_state.mistral_api_key:
            st.error("❌ Please enter your Mistral API key to proceed")
        else:
            with st.spinner("🔄 Processing medical document... This may take a few minutes for large files."):
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    # Process document
                    chunks = process_medical_document(tmp_path)
                    
                    if not chunks:
                        raise Exception("No content could be extracted from the PDF")
                    
                    st.session_state.processed_docs = chunks
                    st.session_state.document_name = uploaded_file.name
                    
                    # Create vector store
                    embedding_function = get_embedding_function()
                    vectorstore = create_vectorstore(
                        chunks=chunks,
                        embedding_function=embedding_function,
                        vectorstore_path="./medical_vectorstore"
                    )
                    st.session_state.vectorstore = vectorstore
                    st.session_state.processing_complete = True
                    st.session_state.processing_error = None
                    
                    st.success(f"✅ Successfully processed {len(chunks)} knowledge chunks from {uploaded_file.name}")
                    
                except Exception as e:
                    error_msg = f"Error processing document: {str(e)}"
                    st.session_state.processing_error = error_msg
                    st.error(f"❌ {error_msg}")
                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
    
    # Show PDF preview and chat interface if processing is complete
    if st.session_state.processing_complete and uploaded_file is not None:
        st.header("📄 Document Preview")
        display_pdf(uploaded_file)
        
        # Display chat interface
        st.header("💬 Medical Q&A")
        
        # Display chat history
        if st.session_state.chat_history:
            for i, (question, answer, sources) in enumerate(st.session_state.chat_history):
                with st.expander(f"Q: {question[:80]}...", expanded=(i == len(st.session_state.chat_history)-1)):
                    st.markdown(f"**❓ Question:** {question}")
                    st.markdown(f"**🎯 Answer:** {answer}")
                    
                    # Display sources
                    if sources and len(sources) > 0:
                        with st.expander("📚 Reference Sources"):
                            for j, source in enumerate(sources):
                                st.markdown(f"**Source {j+1}:**")
                                st.text(source[:400] + "..." if len(source) > 400 else source)
                                st.divider()
        else:
            st.info("💡 Ask a question about the medical document to get started!")
        
        # Question input
        st.divider()
        col1, col2 = st.columns([4, 1])
        
        with col1:
            question = st.text_input(
                "Ask a medical question:",
                placeholder="e.g., What are the clinical features and management of acute myocardial infarction?",
                key="question_input",
                label_visibility="collapsed"
            )
        
        with col2:
            st.write("")  # Spacing
            st.write("")
            ask_button = st.button("Ask", type="primary", use_container_width=True, key="ask_btn")
        
        if ask_button and question:
            with st.spinner("🔍 Searching medical knowledge..."):
                try:
                    # Generate response
                    response = generate_response(question, st.session_state.vectorstore)
                    
                    # Retrieve sources for display
                    retriever = st.session_state.vectorstore.as_retriever(
                        search_type="similarity",
                        search_kwargs={"k": 3}
                    )
                    
                    # Use the new invoke method
                    relevant_docs = retriever.invoke(question)
                    sources = [doc.page_content for doc in relevant_docs]
                    
                    # Add to chat history
                    st.session_state.chat_history.append(
                        (question, response.content, sources)
                    )
                    
                    # Rerun to update display
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error generating response: {str(e)}")
        
        # Document info sidebar
        st.sidebar.header("📊 Document Info")
        st.sidebar.success(f"✅ **Loaded:** {st.session_state.document_name}")
        st.sidebar.info(f"📚 **Knowledge Chunks:** {len(st.session_state.processed_docs)}")
        
        # Clear conversation button
        if st.sidebar.button("🗑️ Clear Conversation", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()
        
        # Show chat statistics
        if st.session_state.chat_history:
            st.sidebar.divider()
            st.sidebar.metric("💬 Questions Asked", len(st.session_state.chat_history))

if __name__ == "__main__":
    main()