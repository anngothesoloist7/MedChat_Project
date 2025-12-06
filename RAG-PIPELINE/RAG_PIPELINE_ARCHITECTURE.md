# 🏛️ **RAG Pipeline Architecture & Setup**

> **Blueprint of the System Infrastructure**

![Architecture](https://img.shields.io/badge/Architecture-Modular-orange?style=for-the-badge)
![Config](https://img.shields.io/badge/Config-Env_Based-yellow?style=for-the-badge)
![Costs](https://img.shields.io/badge/Costs-Pay_Per_Use-green?style=for-the-badge)

---

## 📂 **Directory Architecture**

The project follows a clean, modular structure designed for scalability.

```bash
rag-pipeline/
├── 📄 rag-main.py               # 🎮 Main Orchestrator (CLI Entry Point)
├── 📄 pyproject.toml            # 📦 Dependency Definitions
├── 📄 .env                      # 🔐 Secrets & Configuration
├── 📁 modules/                  # 🧱 Core Logic Modules
│   ├── 📄 splitter_metadata.py  #    ├─ PDF Splitting & Metadata
│   ├── 📄 ocr_parser.py         #    ├─ Mistral OCR & Chunking
│   ├── 📄 embedding_qdrant.py   #    └─ Embedding & Indexing
│   └── 📁 utils/                # 🛠️ Helpers (Logging, File I/O, Hashing)
├── 📁 database/                 # 💾 Data Persistence Layer
│   ├── 📁 raw/                  #    ├─ 📥 Input PDFs
│   ├── 📁 splitted/             #    ├─ ✂️ Split Segments
│   └── 📁 parsed/               #    └─ 📄 JSON/MD Outputs
├── 📁 models/                   # 🧠 Local Model Cache (Sparse Splade)
├── 📁 prompts/                  # 📝 LLM Prompt Templates
└── 📁 logs/                     # 📋 Execution Logs
```

---

## 💾 **Installation**

We use **uv** for lightning-fast dependency management.

### **1. Prerequisites**
- **Python 3.11+**
- **uv** (Universal Package Manager)

### **2. Setup Environment**

```bash
# Clone the repository (if not already done)
git clone <repo-url>
cd rag-pipeline

# Initialize virtual environment and install dependencies
uv sync
```

### **3. Add/Remove Packages**

```bash
# Add a new package
uv add package_name

# Remove a package
uv remove package_name
```

---

## ⚙️ **Initialization & Config**

Configuration is managed via a `.env` file. Copy the example to start.

### **1. Create Config File**

```bash
cp .env.example .env
```

### **2. Configure Variables**

Edit `.env` with your API keys and preferences.

| Variable | Description | Default |
| :--- | :--- | :--- |
| **API Keys** | | |
| `MISTRAL_API_KEY` | Key for Mistral OCR services. | `Required` |
| `GOOGLE_CHAT_API_KEY` | Gemini API Key (Free Tier) for Translation/Metadata. | `Required` |
| `GOOGLE_EMBEDDING_API_KEY` | Gemini API Key (Paid Tier 1) for fast embeddings. | `Required` |
| `QDRANT_API_KEY` | Key for Vector DB access. | `Required` |
| **Pipeline Settings** | | |
| `TARGET_CHUNK_SIZE_MB` | Split PDF size target (MB). | `50` |
| `MAX_PAGES` | Max pages per split PDF. | `500` |
| `CHUNK_SIZE` | Text chunk size (characters). | `1000` |
| `CHUNK_OVERLAP` | Overlap between chunks. | `200` |
| **Model Selection** | | |
| `MISTRAL_MODEL` | OCR Model version. | `mistral-ocr-latest` |
| `GEMINI_METADATA_MODEL` | Model for metadata extraction. | `gemini-pro-1.5` |
| `GEMINI_TRANSLATOR_MODEL` | Model for text translation. | `gemini-2.0-flash` |
| `GEMINI_EMBEDDING_MODEL` | Dense embedding model. | `gemini-embedding-001` |
| `DENSE_VECTOR_SIZE` | Embedding dimensionality. | `1536` |

---

## 💰 **Cost Estimate**

The pipeline uses pay-as-you-go AI services. Here is an estimation of operational costs.

### **1. Mistral OCR** 👁️
- **Pricing**: ~$10 per 1,000 pages (approx).
- **Impact**: High fidelity parsing is the most expensive component but essential for quality.
- **Optimization**: Only re-process new files.

### **2. Google Gemini** 🧠
- **Flash (Translation)**: Extremely cheap (~$0.10 / 1M tokens). High volume tolerant.
- **Pro (Metadata)**: Moderate cost (~$3.50 / 1M input tokens). Used only once per document split.
- **Embeddings**: Very low cost (~$0.00013 / 1k sentences).

### **3. Qdrant Cloud** ☁️
- **Free Tier**: Up to 1GB storage (enough for ~50-100 textbooks).
- **Standard**: Starts at ~$25/mo for managed clusters.

### **📉 Monthly Estimate (Example)**
*Processing 10 Textbooks (500 pages each, 5,000 pages total)*

| Component | Est. Cost |
| :--- | :--- |
| OCR (5k pages) | ~$50.00 |
| Translation (if needed) | ~$2.00 |
| Metadata & Embedding | ~$0.50 |
| **Total One-Time Cost** | **~$52.50** |

> *Note: Costs are estimates and subject to API provider pricing changes.*

---
