# Hybrid RAG AI Assistant

A Python-based hybrid retrieval system combining document ingest, web search, and LLM-driven response generation.

## Project Summary

This repository implements a hybrid retrieval architecture with:
- A FastAPI backend for file upload, chat, and document management
- A Streamlit front-end for interacting with the assistant
- A document pipeline that indexes PDFs, text, markdown, CSV, JSON, and DOCX
- A web scraping pipeline that uses Serper search and extractive HTML parsing
- A Gemini-based LLM orchestration layer for intent routing and answer generation

## Architecture Overview

### Backend (`app/`)

- `app/main.py` — FastAPI application exposing API endpoints:
  - `/health` — backend health and status
  - `/upload` — file upload and document indexing
  - `/chat` — hybrid Q&A endpoint
  - `/documents` — list active indexed documents
  - `/documents` (DELETE) — clear indexed documents

- `app/ai_engine.py` — core AI orchestration:
  - intent classification
  - document retrieval
  - web retrieval
  - hybrid fusion of document + web content
  - answer generation via Gemini LLM prompts

- `app/retrieval.py` — vector search and document processing:
  - text splitting and chunking
  - embedding creation with `sentence-transformers`
  - FAISS-based vector store indexing
  - document retrieval for PDFs, text, markdown, CSV, JSON, DOCX
  - web document retrieval and fusion

- `app/scraping.py` — web retrieval and content extraction:
  - Serper search for live query results
  - async HTML fetching with `aiohttp`
  - extraction using `trafilatura` and BeautifulSoup
  - quality scoring and content validation

### Front-end

- `streamlit_app.py` — Streamlit user interface:
  - checks backend health
  - displays chat history and sources
  - supports file upload status and document state
  - connects to backend endpoints

### Support files

- `requirements.txt` — Python package dependencies
- `test.py` — Gemini API key validation test
- `data/` — storage for uploaded documents and vector indexes
- `output/` — generated results and output artifacts

## Key Features

- Hybrid retrieval: combines document knowledge with live web data
- Multi-format document ingestion: PDF, text, markdown, CSV, JSON, DOCX
- Embedding-based search using FAISS
- Intent-aware query routing: general, RAG-only, hybrid, summary, comparison
- Streamlit UI for fast prototyping and interactive testing

## Supported File Types

- `.pdf`
- `.txt`
- `.md`
- `.csv`
- `.json`
- `.docx`

## Installation

1. Create a Python virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create a `.env` file in the repository root with the following keys:

```text
GEMINI_API_KEY=your_gemini_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

4. Ensure the `data/` and `output/` directories exist. They are created automatically when needed.

## Running the System

### Start the backend API

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Start the Streamlit front-end

```powershell
streamlit run streamlit_app.py
```

Then open the Streamlit URL in your browser.

## Quick Usage

1. Upload documents via the front-end.
2. Use `/upload` to ingest the file and build a FAISS index.
3. Ask questions in the chat interface.
4. The assistant routes queries to one of:
   - general web search
   - document-only retrieval
   - hybrid document + web reasoning
   - summary or comparison mode

## Example Backend Commands

- Health check:
  - `GET http://127.0.0.1:8000/health`
- List documents:
  - `GET http://127.0.0.1:8000/documents`
- Clear document index:
  - `DELETE http://127.0.0.1:8000/documents`

## Development Notes

- The document index is rebuilt for each uploaded file.
- FAISS index data is stored in `data/faiss_index`.
- Active documents are tracked via `RetrievalEngine.active_documents`.
- The assistant uses Gemini (`google-genai`) for both intent routing and final answer generation.

