# RAG Pipeline Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture Design](#architecture-design)
3. [Features](#features)
4. [Pipeline Phases](#pipeline-phases)
5. [Directory Structure](#directory-structure)
6. [Configuration](#configuration)
7. [Usage Guide](#usage-guide)
8. [Module Reference](#module-reference)
9. [Advanced Features](#advanced-features)
10. [Logging & Monitoring](#logging--monitoring)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The **RAG Pipeline** is a comprehensive document processing system designed specifically for medical textbooks and academic papers. It transforms large PDF documents into searchable, structured knowledge stored in a vector database (Qdrant) for Retrieval-Augmented Generation (RAG) applications.

### Key Capabilities

- **Intelligent PDF Splitting**: Splits large PDFs into manageable chunks based on size and page limits
- **Advanced OCR**: Extracts text and images from PDF documents using Mistral AI OCR
- **Metadata Extraction**: Automatically extracts bibliographic metadata (authors, publication year, keywords)
- **Medical Translation**: Translates Vietnamese medical content to English with high precision
- **Vector Embeddings**: Creates hybrid embeddings (dense + sparse) for optimal retrieval
- **Smart Deduplication**: Hash-based deduplication to prevent duplicate content indexing
- **Verification & Retry**: Automated verification of indexed chunks with retry logic

---

## Architecture Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      INPUT SOURCES                          │
│  • Local PDFs  • Google Drive Files  • URLs                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1: SPLITTING                       │
│  ┌──────────────┐    ┌────────────────┐                     │
│  │ PDF Splitter │───▶│ Metadata       │                     │
│  │ • Size-based │    │ Extraction     │                     │
│  │ • Page-based │    │ (Gemini)       │                     │
│  └──────────────┘    └────────────────┘                     │
│         │                                                   │
│         ▼                                                   │
│  Split PDFs (.pdf) + Metadata (.json)                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  PHASE 2: OCR & PARSING                     │
│  ┌──────────────┐    ┌────────────────┐                     │
│  │ OCR Parser   │───▶│ Translation    │                     │
│  │ (Mistral)    │    │ (Gemini)       │                     │
│  │ • Text       │    │ Optional       │                     │
│  │ • Images     │    └────────────────┘                     │
│  └──────────────┘              │                            │
│         │                      │                            │
│         ▼                      ▼                            │
│  ┌────────────────────────────────────┐                     │
│  │ Text Splitter (LangChain)          │                     │
│  │ • RecursiveCharacterTextSplitter   │                     │
│  │ • chunk_size: 1000                 │                     │
│  │ • chunk_overlap: 200               │                     │
│  └────────────────────────────────────┘                     │
│         │                                                   │
│         ▼                                                   │
│  Chunks (.json) + Pages (.json) + Markdown (.md)            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  PHASE 3: EMBEDDING                         │
│  ┌──────────────┐    ┌────────────────┐                     │
│  │ Dense        │    │ Sparse         │                     │
│  │ Embeddings   │    │ Embeddings     │                     │
│  │ (Gemini)     │    │ (SPLADE)       │                     │
│  │ 1536D        │    │ BM25-based     │                     │
│  └──────┬───────┘    └────────┬───────┘                     │
│         │                     │                             │
│         └──────────┬──────────┘                             │
│                    ▼                                        │
│         ┌────────────────────┐                              │
│         │ Qdrant Vector DB   │                              │
│         │ • Hybrid Search    │                              │
│         │ • Deduplication    │                              │
│         │ • Verification     │                              │
│         └────────────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input** → PDF files from various sources (local, Google Drive, URLs)
2. **Splitting** → Large PDFs split into manageable chunks with metadata
3. **OCR** → Extract text and images, optionally translate
4. **Chunking** → Text split into optimal-sized chunks for RAG
5. **Embedding** → Chunks converted to vector embeddings
6. **Storage** → Indexed in Qdrant for retrieval

---

## Features

### 1. **Multi-Source Input Support**

- ✅ Local PDF files
- ✅ Local directories (batch processing)
- ✅ Google Drive folders (automatic listing and download)
- ✅ Direct URLs
- ✅ Interactive file selection

### 2. **Intelligent PDF Splitting**

- **Size-based splitting**: Target chunk size (default: 50MB)
- **Page-based splitting**: Maximum pages per chunk (default: 500 pages)
- **Smart filename generation**: Includes page ranges and metadata
- **Fallback mechanisms**: pypdf → pypdfium2 for better compatibility

### 3. **Advanced OCR Processing**

- **Mistral AI OCR**: State-of-the-art OCR for medical documents
- **Image extraction**: Preserves images with base64 encoding
- **Markdown generation**: Structured output for readability
- **Rate limiting**: Automatic throttling to respect API limits (20 req/min)

### 4. **Metadata Extraction**

- **AI-powered extraction**: Uses Gemini with structured prompts
- **Web search integration**: Automatically searches for missing metadata
- **Extracted fields**:
  - Author (cleaned of titles: MD, PhD, etc.)
  - Book name (cleaned and standardized)
  - Publish year (validated via search)
  - Keywords (disease, symptom, treatment, imaging, lab-test, drug)
  - Language (vietnamese, english, other)

### 5. **Medical Translation**

- **Vietnamese → English**: Specialized medical terminology
- **Batch processing**: Parallel translation with progress tracking
- **Clinical accuracy**: Preserves technical terms and precision
- **Rate limit handling**: Exponential backoff for 429 errors

### 6. **Hybrid Vector Embeddings**

- **Dense embeddings**: Gemini text-embedding-004 (768 dimensions)
- **Sparse embeddings**: SPLADE++ (BM25-based, keyword matching)
- **Hybrid retrieval**: Combines semantic similarity + keyword matching
- **Batch processing**: Configurable batch size for efficiency

### 7. **Deduplication & Verification**

- **Hash-based deduplication**: Prevents duplicate content
- **Post-indexing verification**: Checks all chunks are indexed
- **Automatic retry**: Reprocesses missing chunks
- **Detailed logging**: Tracks indexing status

### 8. **Flexible Pipeline Execution**

- **Phase selection**: Run specific phases (1, 2, or 3)
- **Resumable**: Skip completed phases, reuse existing outputs
- **Cleanup option**: Remove temporary files after processing
- **Interactive mode**: User-friendly prompts and confirmations

---

## Pipeline Phases

### Phase 1: PDF Splitting & Metadata Extraction

**Purpose**: Break large PDFs into manageable chunks and extract metadata

**Process**:

1. Load PDF and calculate total pages/size
2. Split based on size and page constraints
3. Generate descriptive filenames with page ranges
4. Extract metadata using Gemini AI:
   - Parse first/last pages of split
   - Search web for missing information
   - Validate and clean extracted data
5. Save split PDFs and metadata JSON

**Outputs**:

- `database/splitted/{filename}(page_X-Y).pdf`
- `database/splitted/{filename}(page_X-Y)_metadata.json`

**Configuration**:

```env
TARGET_CHUNK_SIZE_MB=50    # Target size per chunk
MAX_PAGES=500              # Max pages per chunk
GEMINI_METADATA_MODEL=gemini-pro-latest
```

### Phase 2: OCR & Parsing

**Purpose**: Extract text and images, optionally translate, and create chunks

**Process**:

1. Upload PDF to Mistral API
2. Retrieve OCR results (markdown + JSON pages)
3. **Optional**: Translate Vietnamese content to English
4. Parse markdown into Document objects
5. Split into chunks using RecursiveCharacterTextSplitter
6. Save outputs with metadata

**Outputs**:

- `database/parsed/{filename}_pages.json` - Raw OCR pages
- `database/parsed/{filename}_full.md` - Full markdown
- `database/parsed/{filename}_chunks.json` - RAG-ready chunks

**Configuration**:

```env
MISTRAL_API_KEY=xxx
MISTRAL_MODEL=mistral-ocr-latest
MAX_REQUESTS_PER_MINUTE=20
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

**Translation** (Optional):

```env
GOOGLE_CHAT_API_KEY=xxx
GEMINI_TRANSLATOR_MODEL=gemini-2.5-flash
```

### Phase 3: Embedding & Indexing

**Purpose**: Create vector embeddings and index in Qdrant

**Process**:

1. Load chunks from JSON
2. Load metadata for the book
3. Generate hybrid embeddings:
   - Dense: Gemini embeddings (768D)
   - Sparse: SPLADE++ embeddings
4. Create Qdrant points with full payload
5. Upsert to collection with deduplication
6. Verify indexing success

**Outputs**:

- Points stored in Qdrant collection
- `logs/indexing_status.log` - Verification logs

**Configuration**:

```env
GOOGLE_EMBEDDING_API_KEY=xxx
SERVICE_URL_QDRANT=https://xxx.cloud.qdrant.io
QDRANT_API_KEY=xxx
COLLECTION_NAME=medical_rag
GEMINI_BATCH_SIZE=100
QDRANT_BATCH_SIZE=100
```

**Point Structure**:

```json
{
  "id": "hash_of_book_page_text",
  "vector": {
    "dense": [1536D float array],
    "sparse": {"indices": [...], "values": [...]}
  },
  "payload": {
    "page_content": "chunk text",
    "page_number": 42,
    "book_name": "Robbins Basic Pathology",
    "author": "Vinay Kumar et al.",
    "publish_year": "15-03-2018",
    "keywords": ["disease", "symptom", "treatment"],
    "language": "english",
    "file_name": "robbins_pathology(page_1-500).pdf"
  }
}
```

---

## Directory Structure

```
rag-pipeline/
├── rag-main.py                 # Main entry point
├── .env                        # Environment configuration
├── database/
│   ├── raw/                    # Downloaded/input PDFs
│   ├── splitted/               # Split PDFs + metadata
│   └── parsed/                 # OCR outputs (JSON, MD, chunks)
├── logs/
│   ├── indexing_status.log     # Verification logs
│   └── pipeline.log            # Pipeline execution logs
├── models/                     # Cached embedding models
├── modules/
│   ├── splitter_metadata.py    # Phase 1: Splitting
│   ├── ocr_parser.py           # Phase 2: OCR
│   ├── embedding_qdrant.py     # Phase 3: Embedding
│   └── utils/
│       ├── file_utils.py       # File/URL handling
│       ├── hash_utils.py       # Deduplication
│       ├── pipeline_logger.py  # Logging
│       ├── qdrant_verifier.py  # Verification
│       └── translator.py       # Translation
└── prompts/
    ├── metadata_extract_prompt.md
    └── medical_info_translation_prompt.md
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Base Directory
BASE_DIR=/path/to/rag-pipeline

# Splitting Configuration
TARGET_CHUNK_SIZE_MB=50
MAX_PAGES=500

# Mistral OCR
MISTRAL_API_KEY=your_mistral_key
MISTRAL_MODEL=mistral-ocr-latest
MAX_REQUESTS_PER_MINUTE=20

# Gemini Models
GOOGLE_CHAT_API_KEY=your_gemini_key
GOOGLE_EMBEDDING_API_KEY=your_gemini_key
GEMINI_METADATA_MODEL=gemini-pro-latest
GEMINI_TRANSLATOR_MODEL=gemini-2.5-flash

# Text Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Qdrant Configuration
SERVICE_URL_QDRANT=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_key
COLLECTION_NAME=medical_rag
GEMINI_BATCH_SIZE=100
QDRANT_BATCH_SIZE=100
```

### Model Configuration

**Embedding Model**: Gemini `gemini-embedding-001` (1536 dimensions)

- Task type: `RETRIEVAL_DOCUMENT` for indexing
- Task type: `RETRIEVAL_QUERY` for search

**Sparse Model**: SPLADE++ (`prithivida/Splade_PP_en_v1`)

- Cached locally in `models/` directory
- BM25-based for keyword matching

---

## Usage Guide

### Basic Usage

```bash
# Run full pipeline (all phases)
python rag-main.py /path/to/file.pdf

# Or enter path interactively
python rag-main.py
> Enter path or URL: /path/to/file.pdf
```

### Process Specific Phase

```bash
# Only Phase 1 (Splitting)
python rag-main.py /path/to/file.pdf --phase 1

# Only Phase 2 (OCR)
python rag-main.py /path/to/file.pdf --phase 2

# Only Phase 3 (Embedding)
python rag-main.py /path/to/file.pdf --phase 3
```

### Cleanup Temporary Files

```bash
# Remove temporary files after processing
python rag-main.py /path/to/file.pdf --clean 1
```

### Process Multiple Files

```bash
# Process directory
python rag-main.py /path/to/pdf-directory/

# Interactive selection
> Found 10 files:
> 1. textbook1.pdf
> 2. textbook2.pdf
> ...
> How many files to process? (Enter number 1-10 or 'all'): 3
```

### Google Drive Integration

```bash
# Single file
python rag-main.py https://drive.google.com/file/d/FILE_ID/view

# Entire folder
python rag-main.py https://drive.google.com/drive/folders/FOLDER_ID
```

### Resume Processing

If Phase 1 is already completed:

```bash
# Skip to Phase 2
python rag-main.py /path/to/file.pdf --phase 2

# Or run without --phase to auto-detect existing splits
python rag-main.py /path/to/file.pdf
> [INFO] Phase 1: Skipped (Checking existing...)
> [INFO] Found 3 existing files.
```

---

## Module Reference

### 1. `splitter_metadata.py`

**Class: PDFProcessor**

**Methods**:

- `get_pdf_info(path)`: Get total pages and file size
- `calculate_ranges(total_pages, total_size)`: Calculate split ranges
- `split_pdf(input_path, output_dir)`: Split PDF and save chunks

**Functions**:

- `extract_metadata(file_path, pdf_id)`: Extract metadata using Gemini
- `run_splitter(input_path_str)`: Main entry point for Phase 1

**Example**:

```python
from modules.splitter_metadata import run_splitter

split_files = run_splitter("/path/to/large.pdf")
# Returns: ["/path/to/splitted/large(page_1-500).pdf", ...]
```

### 2. `ocr_parser.py`

**Class: RateLimitTracker**

- Manages API rate limits (20 requests/minute for Mistral)

**Functions**:

- `get_mistral_client()`: Initialize Mistral client
- `upload_pdf(client, file_path)`: Upload PDF for OCR
- `parse_markdown_for_rag(pages_data, source_file)`: Convert to Document objects
- `process_file(file_path)`: Main OCR processing logic
- `run_ocr_parser(files)`: Entry point for Phase 2

**Example**:

```python
from modules.ocr_parser import run_ocr_parser

split_files = ["/path/to/chunk1.pdf", "/path/to/chunk2.pdf"]
run_ocr_parser(split_files)
# Generates: chunk1_chunks.json, chunk1_pages.json, chunk1_full.md
```

### 3. `embedding_qdrant.py`

**Class: QdrantManager**

**Methods**:

- `__init__()`: Initialize clients and models
- `check_connections()`: Verify Gemini and Qdrant connectivity
- `init_collection()`: Create/configure Qdrant collection
- `get_embeddings_batch(texts)`: Generate dense embeddings
- `load_metadata(book_name)`: Load metadata JSON
- `generate_id(book_name, page_num, text)`: Generate unique hash ID
- `process_batch(batch, book_meta, batch_index)`: Embed and upsert batch
- `process_and_index(json_path)`: Process single chunk file

**Functions**:

- `run_embedding(files)`: Entry point for Phase 3

**Example**:

```python
from modules.embedding_qdrant import run_embedding

chunk_files = ["/path/to/chunk1.pdf", "/path/to/chunk2.pdf"]
run_embedding(chunk_files)
# Indexes chunks in Qdrant
```

### 4. `utils/translator.py`

**Class: Translator**

**Methods**:

- `translate_pages(pages, batch_size)`: Translate page list in parallel
- `translate_content(text)`: Translate single text with retry

**Example**:

```python
from modules.utils.translator import translator

pages = [{"page": 1, "content": "Vietnamese text..."}]
translated_pages, full_md = translator.translate_pages(pages)
```

### 5. `utils/file_utils.py`

**Functions**:

- `is_url(path)`: Check if string is URL
- `download_file(url, output_dir)`: Download from URL or Google Drive
- `list_google_drive_folder(url)`: List files in GDrive folder
- `download_google_drive_file(file_url, output_dir)`: Download single GDrive file
- `resolve_pdf_path(input_path, download_dir)`: Resolve local or remote path

### 6. `utils/qdrant_verifier.py`

**Functions**:

- `setup_logger(log_dir)`: Configure logging
- `verify_and_retry_indexing(qdrant_manager, json_files, log_dir)`: Verify and retry missing chunks

**Example**:

```python
from modules.embedding_qdrant import QdrantManager
from modules.utils.qdrant_verifier import verify_and_retry_indexing

manager = QdrantManager()
json_files = ["/path/to/chunk1_chunks.json"]
success = verify_and_retry_indexing(manager, json_files)
```

---

## Advanced Features

### 1. Custom Chunking Strategy

Modify `ocr_parser.py`:

```python
# Custom splitter configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,        # Larger chunks
    chunk_overlap=300,       # More overlap
    separators=["\n\n", "\n", ". ", " ", ""]  # Custom separators
)
```

### 2. Custom Metadata Fields

Modify `prompts/metadata_extract_prompt.md` to extract additional fields:

```markdown
6. **EDITION:**
   - Extract the edition number (e.g., "10th Edition")
```

Then update the schema in `splitter_metadata.py`.

### 3. Parallel Processing

For multiple files, the pipeline processes sequentially. To parallelize:

```python
from concurrent.futures import ProcessPoolExecutor

def process_pdf_wrapper(args):
    pdf_file, phases = args
    process_pdf(pdf_file, phases)

with ProcessPoolExecutor(max_workers=3) as executor:
    executor.map(process_pdf_wrapper, [(f, phases) for f in final_files])
```

### 4. Custom Collection Configuration

Modify `embedding_qdrant.py` `init_collection()`:

```python
self.qdrant_client.create_collection(
    collection_name=self.Config.COLLECTION_NAME,
    vectors_config={
        "dense": models.VectorParams(
            size=768,
            distance=models.Distance.COSINE,
            on_disk=True  # Store on disk for large collections
        )
    },
    sparse_vectors_config={
        "sparse": models.SparseVectorParams()
    },
    optimizers_config=models.OptimizersConfigDiff(
        indexing_threshold=50000  # Optimize for large collections
    )
)
```

---

## Logging & Monitoring

### Pipeline Logs

**Location**: `logs/pipeline.log`

**Format**:

```
2025-12-03 15:30:00 - INFO - Processing PDF: textbook.pdf
2025-12-03 15:30:05 - PHASE - Split - STARTED - File: textbook.pdf
2025-12-03 15:30:45 - PHASE - Split - COMPLETED - Generated 3 files
2025-12-03 15:30:46 - PHASE - OCR - STARTED - Files: 3
2025-12-03 15:35:12 - PHASE - OCR - COMPLETED
2025-12-03 15:35:13 - PHASE - Embedding - STARTED
2025-12-03 15:38:30 - PHASE - Embedding - COMPLETED
```

### Indexing Verification Logs

**Location**: `logs/indexing_status.log`

**Contents**:

- Total chunks expected
- Missing chunks detected
- Retry attempts and results
- Final verification status

### Console Output

```
==========================================
Processing: robbins_pathology.pdf
==========================================

[INFO] Phase 1: Splitting...
[INFO] PDF Info: 2000 pages, 250 MB
[INFO] Generated 4 files.

[INFO] Phase 2: OCR & Parsing...
[1/4] Processing robbins_pathology(page_1-500).pdf
  Uploading... ⣾
  OCR Complete in 45.2s
  Translation: SKIPPED (English detected)
  Chunking... 245 chunks created

[INFO] Phase 3: Embedding...
[1/4] Processing robbins_pathology(page_1-500)_chunks.json
  Batch 1/3: ████████████████████ 100% | 100 chunks
  Batch 2/3: ████████████████████ 100% | 100 chunks
  Batch 3/3: ████████████████████ 100% | 45 chunks
  ✓ Indexed 245 chunks

[VERIFY] Starting verification...
[VERIFY] Checking 245 chunks in Qdrant...
[SUCCESS] All 245 chunks verified successfully.

[INFO] Pipeline Completed
```

---

## Troubleshooting

### Issue: "Missing chunks after indexing"

**Cause**: Network errors, API rate limits, or Qdrant connection issues

**Solution**:

```python
from modules.embedding_qdrant import QdrantManager
from modules.utils.qdrant_verifier import verify_and_retry_indexing

manager = QdrantManager()
json_files = ["database/parsed/file_chunks.json"]
verify_and_retry_indexing(manager, json_files)
```

### Issue: "Rate limit exceeded" (429 errors)

**Cause**: Too many requests to Gemini or Mistral

**Solution**:

- Mistral: Automatic backoff in `RateLimitTracker`
- Gemini: Exponential backoff in `translator.py`
- Reduce batch sizes in `.env`:
  ```env
  GEMINI_BATCH_SIZE=50
  MAX_REQUESTS_PER_MINUTE=10
  ```

### Issue: "Translation timeout"

**Cause**: Large batches or slow API response

**Solution**:

- Reduce translation batch size:
  ```python
  translator.translate_pages(pages, batch_size=3)
  ```
- Increase timeout in `translator.py`

### Issue: "Split files not found"

**Cause**: Phase 1 not completed or files deleted

**Solution**:

```bash
# Re-run Phase 1
python rag-main.py /path/to/file.pdf --phase 1
```

### Issue: "Collection not found"

**Cause**: Qdrant collection not initialized

**Solution**:

```python
from modules.embedding_qdrant import QdrantManager

manager = QdrantManager()
manager.init_collection()
```

### Issue: "Memory errors during embedding"

**Cause**: Large batch sizes

**Solution**:

```env
GEMINI_BATCH_SIZE=50
QDRANT_BATCH_SIZE=50
```

---

## Best Practices

1. **Start with small batches**: Test with 1-2 files before processing entire libraries
2. **Monitor API usage**: Track Gemini/Mistral API quotas
3. **Verify indexing**: Always run verification after Phase 3
4. **Backup metadata**: Keep copies of `*_metadata.json` files
5. **Use cleanup wisely**: Only use `--clean 1` after confirming successful indexing
6. **Check logs**: Review `pipeline.log` for errors and warnings
7. **Optimize costs**: Use smaller models for metadata extraction if budget is tight

---

## API Cost Estimation

**Per 1000-page PDF**:

- Mistral OCR: ~$0.50 (at $0.5/1K pages)
- Gemini Metadata: ~$0.01 (1-2 requests)
- Gemini Embeddings: ~$0.10 (2000 chunks × $0.00005/chunk)
- **Total**: ~$0.61 per 1000 pages

**Translation** (Optional):

- Gemini Translation: ~$0.20 per 1000 pages
- **Total with translation**: ~$0.81 per 1000 pages

---

## Performance Metrics

**Processing Speed** (Single 1000-page PDF):

- Phase 1 (Splitting): ~30 seconds
- Phase 2 (OCR): ~15 minutes (depends on API speed)
- Phase 3 (Embedding): ~5 minutes
- **Total**: ~20 minutes

**With Translation**:

- Phase 2 (OCR + Translation): ~25 minutes
- **Total**: ~30 minutes

---

## Future Enhancements

- [ ] Multi-language support (French, German, Spanish)
- [ ] Custom embedding models (OpenAI, Cohere)
- [ ] Image-to-text embedding for diagrams
- [ ] Incremental indexing (add new chunks without reprocessing)
- [ ] Web UI for pipeline management
- [ ] Distributed processing with Celery
- [ ] Support for EPUB, DOCX formats

---

## Support

For issues or questions:

1. Check logs in `logs/` directory
2. Review this documentation
3. Open an issue on GitHub
4. Contact the development team

---

**Last Updated**: December 3, 2025  
**Version**: 1.0  
**License**: MIT

---

## API Usage

The pipeline can now be exposed as a REST API using FastAPI.

### Starting the API

```bash
uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Endpoints

#### `POST /process`

Trigger the pipeline for a file or URL.

**Parameters:**

- `file`: (Optional) Upload a PDF file.
- `url`: (Optional) URL to a PDF or Google Drive file/folder.
- `p1`: (Optional, default=True) Run Phase 1 (Splitting).
- `p2`: (Optional, default=True) Run Phase 2 (OCR).
- `p3`: (Optional, default=True) Run Phase 3 (Embedding).
- `clean`: (Optional, default=False) Cleanup temporary files.

**Example:**

```bash
curl -X POST "http://localhost:8000/process" \
     -F "url=https://example.com/file.pdf" \
     -F "clean=true"
```
