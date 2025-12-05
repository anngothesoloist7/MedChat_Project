# MedChat RAG Pipeline

A specialized, high-performance document processing engine designed to ingest medical text books and papers, converting them into a queryable, structured Retrieval-Augmented Generation (RAG) system.

**Core Mission:**

- **Ingest**: Handle large medical PDFs.
- **Understand**: OCR, parse, and translate specialized content.
- **Index**: Create hybrid semantic search indices (Dense + Sparse) for instant retrieval.

---

## Architecture

The pipeline executes in three distinct, resumable phases, turning raw PDFs into indexed vector knowledge.

### 1. Input Handling & Initialization

```mermaid
%%{
  init: {
    'theme': 'base',
    'themeVariables': {
      'primaryColor': '#D5E8D4',
      'primaryTextColor': '#000000',
      'primaryBorderColor': '#82B366',
      'lineColor': '#555555',
      'secondaryColor': '#FFF2CC',
      'tertiaryColor': '#DAE8FC',
      'fontFamily': 'Inter, sans-serif'
    }
  }
}%%
flowchart TD
    classDef default fill:#D5E8D4,stroke:#82B366,stroke-width:1px,color:#000;
    classDef decision fill:#FFF2CC,stroke:#D6B656,stroke-width:1px,color:#000;
    classDef action fill:#DAE8FC,stroke:#6C8EBF,stroke-width:1px,color:#000;
    classDef terminator fill:#F5F5F5,stroke:#666666,stroke-width:1px,color:#333;

    Start([Start: rag-main.py CLI]):::terminator --> Init[Initialize: Load .env, Config]
    Init --> InputPrompt[/Prompt: Input Path or URL/]
    InputPrompt --> InputType{Check Input Type}:::decision
    
    InputType -- "URL / Link" --> URLRes[resolve_pdf_path]:::action
    InputType -- "Google Drive" --> GDDown[download_google_drive_file]:::action
    InputType -- "Local File/Dir" --> Local[Validate Local Path]:::action
    
    URLRes --> ListFiles[Generate File List]
    GDDown --> ListFiles
    Local --> ListFiles
    
    ListFiles --> Select{User Selection}:::decision
    Select -- "Select All / Specific" --> Prepare[Finalize List of PDFs]
    Prepare --> NextPhase([Proceed to Phase 1]):::terminator
```

### 2. Phase 1: Splitting & Metadata

```mermaid
%%{
  init: {
    'theme': 'base',
    'themeVariables': {
      'primaryColor': '#D5E8D4',
      'primaryTextColor': '#000000',
      'primaryBorderColor': '#82B366',
      'lineColor': '#555555',
      'secondaryColor': '#FFF2CC',
      'tertiaryColor': '#DAE8FC',
      'fontFamily': 'Inter, sans-serif'
    }
  }
}%%
flowchart TD
    classDef default fill:#D5E8D4,stroke:#82B366,stroke-width:1px,color:#000;
    classDef decision fill:#FFF2CC,stroke:#D6B656,stroke-width:1px,color:#000;
    classDef action fill:#DAE8FC,stroke:#6C8EBF,stroke-width:1px,color:#000;
    classDef error fill:#F8CECC,stroke:#B85450,stroke-width:1px,stroke-dasharray: 5 5,color:#000;

    Start([Start Phase 1]) --> Copy[Copy PDF to database/raw]:::action
    Copy --> CheckQ{Check Qdrant Existence}:::decision
    
    CheckQ -- "Exists & Overwrite=False" --> Skip[Skip File]:::error
    CheckQ -- "Exists & Overwrite=True" --> Delete[Delete Existing Points]:::action
    CheckQ -- "New File" --> Meta
    
    Delete --> Meta[extract_metadata]:::action
    Meta --> Mistral["Mistral OCR (First 15 Pages)"]
    Mistral --> Gemini["Gemini 2.5 Pro + Google Search"]
    Gemini --> SaveMeta[Save _metadata.json]:::action
    
    SaveMeta --> Calc[Calculate Split Ranges]
    Calc --> Split["Split PDF (PyPDF / pdfium2)"]:::action
    Split --> Output[Save to database/splitted]
```

### 3. Phase 2: OCR & Parsing

```mermaid
%%{
  init: {
    'theme': 'base',
    'themeVariables': {
      'primaryColor': '#D5E8D4',
      'primaryTextColor': '#000000',
      'primaryBorderColor': '#82B366',
      'lineColor': '#555555',
      'secondaryColor': '#FFF2CC',
      'tertiaryColor': '#DAE8FC',
      'fontFamily': 'Inter, sans-serif'
    }
  }
}%%
flowchart TD
    classDef default fill:#D5E8D4,stroke:#82B366,stroke-width:1px,color:#000;
    classDef decision fill:#FFF2CC,stroke:#D6B656,stroke-width:1px,color:#000;
    classDef action fill:#DAE8FC,stroke:#6C8EBF,stroke-width:1px,color:#000;

    Start([Start Phase 2]) --> Loop{For each Split PDF}:::decision
    Loop --> Upload[Upload to Mistral API]:::action
    Upload --> OCR[Mistral OCR Process]
    OCR --> RawMD[Get Raw Markdown]
    
    RawMD --> LangCheck{Check Language}:::decision
    LangCheck -- "Vietnamese" --> Trans[Gemini Flash Translation]:::action
    LangCheck -- "English/Other" --> Chunk
    
    Trans --> Chunk[Recursive Character Split]:::action
    Chunk --> Save[Save _full.md & _chunks.json]:::action
    Save --> Loop
```

### 4. Phase 3: Embedding & Indexing

```mermaid
%%{
  init: {
    'theme': 'base',
    'themeVariables': {
      'primaryColor': '#D5E8D4',
      'primaryTextColor': '#000000',
      'primaryBorderColor': '#82B366',
      'lineColor': '#555555',
      'secondaryColor': '#FFF2CC',
      'tertiaryColor': '#DAE8FC',
      'fontFamily': 'Inter, sans-serif'
    }
  }
}%%
flowchart TD
    classDef default fill:#D5E8D4,stroke:#82B366,stroke-width:1px,color:#000;
    classDef decision fill:#FFF2CC,stroke:#D6B656,stroke-width:1px,color:#000;
    classDef action fill:#DAE8FC,stroke:#6C8EBF,stroke-width:1px,color:#000;
    classDef error fill:#F8CECC,stroke:#B85450,stroke-width:1px,stroke-dasharray: 5 5,color:#000;

    Start([Start Phase 3]) --> Connect[Check Qdrant Connection]:::decision
    Connect -->|Fail| Stop[Stop Pipeline]:::error
    Connect -->|Success| Init["Init Collection (Dense + BM25)"]:::action
    
    Init --> Loop{For each chunk file}:::decision
    Loop --> Load[Load _chunks.json & Metadata]
    Load --> BatchLoop{Batch Process}:::decision
    
    BatchLoop --> Dense[Gemini Embedding 001]:::action
    BatchLoop --> Sparse[SPLADE / BM25 Sparse]:::action
    
    Dense & Sparse --> Point[Create Qdrant Point]
    Point --> Upsert[Upsert to Qdrant]:::action
    Upsert --> BatchLoop
    
    BatchLoop -- Done --> Loop
```

### 5. Verification & Cleanup

```mermaid
%%{
  init: {
    'theme': 'base',
    'themeVariables': {
      'primaryColor': '#D5E8D4',
      'primaryTextColor': '#000000',
      'primaryBorderColor': '#82B366',
      'lineColor': '#555555',
      'secondaryColor': '#FFF2CC',
      'tertiaryColor': '#DAE8FC',
      'fontFamily': 'Inter, sans-serif'
    }
  }
}%%
flowchart TD
    classDef default fill:#D5E8D4,stroke:#82B366,stroke-width:1px,color:#000;
    classDef decision fill:#FFF2CC,stroke:#D6B656,stroke-width:1px,color:#000;
    classDef action fill:#DAE8FC,stroke:#6C8EBF,stroke-width:1px,color:#000;
    classDef terminator fill:#F5F5F5,stroke:#666666,stroke-width:1px,color:#333;

    Start([End of Phase 3]) --> Count[Count Local Chunks]:::action
    Count --> Query["Count Qdrant Points (by PDF ID)"]:::action
    
    Query --> Match{Match?}:::decision
    Match -- "Yes" --> Success[Log Success]
    Match -- "No (Missing)" --> Retry[Retry Missing Assets]:::action
    Retry --> BackToPhase3([Trigger Phase 3 Logic]):::terminator
    
    Success --> CleanPrompt{Clean Temp Files?}:::decision
    CleanPrompt -- "Yes" --> Clean[Delete raw/splitted/parsed]:::action
    Clean --> Finish([Pipeline Complete]):::terminator
```

### Directory Structure

```text
rag-pipeline/
├── rag-main.py                 # Main Orchestrator (CLI Entry Point)
├── pyproject.toml              # Dependency Definitions
├── .env                        # Configuration secrets
├── modules/                    # Core Logic
│   ├── splitter_metadata.py    # Phase 1: Splitting & Metadata
│   ├── ocr_parser.py           # Phase 2: OCR & Chunking
│   ├── embedding_qdrant.py     # Phase 3: Embedding & Indexing
│   └── utils/                  # Helpers (Logging, File I/O)
├── database/                   # Data Persistence
│   ├── raw/                    # Input PDFs
│   ├── splitted/               # Split Segments
│   └── parsed/                 # JSON/MD Outputs
├── models/                     # Local Model Cache (Sparse Splade)
└── prompts/                    # LLM Prompts
```

### Technology Stack

| Category | Technology | Usage |
| :--- | :--- | :--- |
| **Language** | Python 3.11+ | Core logic and orchestration. |
| **OCR** | Mistral AI | State-of-the-art text & image extraction. |
| **LLM** | Google Gemini | Metadata (gemini-2.5-pro with Google Search), Translation (gemini-2.0-flash), Embeddings (gemini-embedding-001). |
| **Vectors** | Gemini + SPLADE | Hybrid Dense (Semantic) + Sparse (Keyword). |
| **DB** | Qdrant | High-speed vector storage. |
| **Tooling** | `uv`, `LangChain` | Package management and text chunking. |

---

## Pipeline Phases

### Phase 1: Smart Splitting

**Purpose:** Break down monolithic textbooks into manageable chunks (~50MB or 500 pages) and extract metadata.

- **Process:**

  1. Validates input PDF.
  2. Splits based on size/page limits.
  3. **Metadata Extraction:** Uses Gemini to read the first few pages and extract:
      - Author, Book Name, Publish Year (cross-referenced with Google Search).
      - Keywords (disease, symptom, drug, etc.).
- **Outputs:** `database/splitted/{filename}(page_X-Y).pdf` and corresponding `_metadata.json`.

### Phase 2: OCR & Parsing

**Purpose:** Convert PDF segments into structured markdown and text chunks.

- **Process:**

  1. **OCR:** Uploads to Mistral OCR API to extract text and images (as base64).
  2. **Translation (Optional):** Detects Vietnamese medical content and translates to English using Gemini Flash.
  3. **Cleaning:** Formats text into clean Markdown.
  4. **Chunking:** Splits text into 1000-char overlapping windows (RecursiveCharacterTextSplitter).
- **Outputs:** `database/parsed/{filename}_full.md` and `_chunks.json`.

### Phase 3: Embedding & Indexing

**Purpose:** Map text chunks to vector space and store in Qdrant.

- **Process:**
  1. **Dense Embedding:** Generates 1536-dim vectors using `gemini-embedding-001`.
  2. **Sparse Embedding:** Generates keyword weights using `SPLADE++` (BM25-style).
  3. **Indexing:** Upserts to Qdrant with a unique hash ID for deduplication.
  4. **Verification:** Verifies 100% of chunks are indexed.

---

## Installation & Setup

We use **uv** for fast dependency management.

1. **Prerequisites:** Python 3.11+, `uv` installed.
2. **Install Dependencies:**

    ```bash
    uv sync
    ```

3. **Configuration (.env):**
    Copy `.env.example` to `.env` and fill in your keys.

| Variable | Description |
| :--- | :--- |
| `MISTRAL_API_KEY` | Mistral OCR API Key |
| `GOOGLE_CHAT_API_KEY` | Gemini API Key for Translation/Metadata using free tier key |
| `GOOGLE_EMBEDDING_API_KEY` | Gemini API Key for Embeddings using tier 1 key for better performance |
| `QDRANT_API_KEY` | Qdrant self-hosted API Key |
| `SERVICE_URL_QDRANT` | Qdrant Cluster URL with Coudflare Tunnels |

---

## Usage Guide

Run the pipeline via the CLI. It handles local files, folders, and URLs (including Google Drive).

### Basic Execution

```bash
# Interactive mode
uv run python rag-main.py

# Direct file path
uv run python rag-main.py "path/to/textbook.pdf"
```

### Advanced Usage

```bash
# Run specific phase (e.g., only embedding)
uv run python rag-main.py "file.pdf" --phase 3

# Process an entire folder
uv run python rag-main.py "path/to/folder/"

# Clean up temporary files after success
uv run python rag-main.py "file.pdf" --clean 1
```

---

## Module Reference

### 1. splitter_metadata.py

#### Class: PDFProcessor

Basic handler for reading PDF properties and managing split ranges.

#### Functions (splitter_metadata)

- `extract_metadata(file_path)`: Calls Gemini to analyze PDF content and fetch metadata.
- `run_splitter(path)`: Orchestrates the splitting validation and execution.

### 2. ocr_parser.py

#### Class: RateLimitTracker

Manages API throttling (e.g., Mistral 20 req/min).

#### Functions (ocr_parser)

- `upload_pdf(client, path)`: Handles file upload to Mistral.
- `process_file(path)`: Main logic for OCR -> Translation -> Chunking.

### 3. embedding_qdrant.py

#### Class: QdrantManager

- `init_collection()`: Configures Qdrant collection with Dense + Sparse vectors.
- `process_batch(batch)`: Handles parallel embedding generation and upsertion.
- `check_connections()`: Validates API connectivity before starting.

### 4. Utilities

- **file_utils**: parsing Google Drive URLs, downloading files.
- **translator**: Batch translation using Gemini Flash with backoff.
- **qdrant_verifier**: Post-indexing check to ensure data integrity.

---

## Cost Analysis (Estimate)

| Component | Cost Factor | Estimate (per 1k pages) |
| :--- | :--- | :--- |
| **Mistral OCR** | $10 / 1k pages | Free (using experimental plan) |
| **Gemini Flash** | Translation (Input/Output) | ~$0.20 |
| **Gemini Embed** | Text Embedding | < $0.05 |
| **Qdrant** | Storage | Free tier (Self-hosted)  |

*Note: Mistral OCR is the primary cost driver. Use wisely.*
