# 🏥 **MedChat RAG Pipeline Overview**

> **Transforming Medical Textbooks into Intelligent Knowledge Bases**

![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Qdrant](https://img.shields.io/badge/Vector_DB-Qdrant-red?style=for-the-badge)
![AI](https://img.shields.io/badge/AI-Gemini_%7C_Mistral-purple?style=for-the-badge)

---

## 🎯 **Purpose**

The **MedChat RAG Pipeline** is a specialized, high-performance document processing engine designed to ingest complex medical textbooks and academic papers. It solves the challenge of unlocking unstructured medical knowledge by converting PDFs into a queryable, structured **Retrieval-Augmented Generation (RAG)** system.

**Core Mission:**
- 📄 **Ingest**: Handle massive medical PDFs.
- 🧠 **Understand**: OCR, parse, and translate specialized content.
- 🔍 **Index**: Create hybrid semantic search indices for instant retrieval.

---

## 🛠️ **Tech Stack**

A curated selection of modern, high-efficiency tools.

| Category | Technology | Usage |
| :--- | :--- | :--- |
| **Language** | ![Python](https://img.shields.io/badge/-Python-3776AB?style=flat&logo=python&logoColor=white) | Core orchestration logic. |
| **OCR** | **Mistral AI OCR** | State-of-the-art text & image extraction from PDFs. |
| **LLM** | **Google Gemini** | Metadata extraction (`Pro`) & Translation (`Flash`). |
| **Embeddings** | **Gemini + SPLADE** | Hybrid Dense (Semantic) + Sparse (Keyword) vectors. |
| **Vector DB** | **Qdrant** | High-speed vector storage and retrieval. |
| **Frameworks** | `LangChain`, `FastAPI` | Text chunking and API interfacing. |
| **Package Mgr** | `uv` | Blazing fast Python package management. |

---

## 🔄 **Workflow Pipeline**

The pipeline executes in three distinct, resumable phases.

![RAG Pipeline Architecture](assets/rag_pipeline_diagram.png)

### **Phase 1: Smart Splitting** 🧩
*Breaks down monolithic textbooks into manageable chunks.*
- **Action**: Splits PDFs by size (~50MB) or page count (500 pages).
- **Intelligence**: Uses **Gemini AI** to extract metadata (Author, Year, Keywords) by reading the first few pages and cross-referencing with Google Search.
- **Output**: Metadata-enriched PDF segments.

### **Phase 2: OCR & Enrichment** 👁️
*Converts pixels to structured meaning.*
- **Action**: Sends segments to **Mistral OCR** for high-fidelity text and image extraction.
- **Translation** (Optional): Translates Vietnamese medical content to English using **Gemini 2.0 Flash**, preserving clinical accuracy.
- **Chunking**: Splits text into 1000-character overlapping windows for optimal retrieval context.

### **Phase 3: Hybrid Embedding** 🧬
*Maps knowledge to vector space.*
- **Dense Vector**: `gemini-embedding-001` (1536d) captures *semantic meaning*.
- **Sparse Vector**: `SPLADE++` captures *exact keyword matches* (BM25-style).
- **Indexing**: Upserts to **Qdrant** with robust deduplication and verification to ensure 100% data integrity.

---

## 🔌 **API Usage & Models**

We leverage a multi-model approach for cost and performance optimization.

### **1. Mistral AI**
- **Endpoint**: OCR Service
- **Usage**: Parsing complex PDF layouts, tables, and sidebars.
- **Rate Limit**: Auto-throttled to 20 requests/minute.

### **2. Google Gemini**
- **Metadata Extraction**: `gemini-1.5-pro` (High intelligence for structured data).
- **Translation**: `gemini-2.0-flash` (Fast, cost-effective for bulk text).
- **Embeddings**: `gemini-embedding-001` (Optimized for retrieval tasks).

### **3. Qdrant Cloud**
- **Role**: Vector Search Engine.
- **Config**: Hybrid search enabled (Dense + Sparse).
- **Payload**: Stores full text + rich metadata (Page #, Book Source, Year).

---

## 🚀 **Quick Start**

Run the full pipeline with a single command:

```bash
# Process a local file, folder, or URL
uv run python rag-main.py "path/to/textbook.pdf"
```

**Interactive Mode:**
```bash
uv run python rag-main.py
> Enter path or URL: ...
```

---
