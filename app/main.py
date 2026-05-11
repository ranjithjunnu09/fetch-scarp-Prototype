import os
import shutil
import asyncio

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from typing import List, Optional

from app.ai_engine import AIEngine


# =====================================================
# APP INIT
# =====================================================

app = FastAPI(
    title="Hybrid RAG AI",
    description="ChatGPT-style Hybrid RAG with intelligent intent routing",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# SINGLETON ENGINE
# =====================================================

engine = AIEngine()

# =====================================================
# UPLOAD DIRECTORY
# =====================================================

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =====================================================
# SUPPORTED FILE TYPES
# =====================================================

SUPPORTED_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/json": ".json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
}

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json", ".docx"}


# =====================================================
# REQUEST MODELS
# =====================================================

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[dict]] = []
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    rewritten_query: str
    reasoning: str
    execution_plan: dict
    sources: List[str]
    retrieved_chunks: List[dict]


# =====================================================
# ROUTES
# =====================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_documents": engine.retrieval.active_documents,
        "model": engine.model_name,
        "vector_store_loaded": engine.retrieval.pdf_vectordb is not None
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Universal file upload endpoint.
    Supports: PDF, TXT, MD, CSV, JSON, DOCX
    """
    # Validate extension
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
        )

    # Save file to disk
    save_path = os.path.join(UPLOAD_DIR, filename)

    try:
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )

    # Process and index the file
    try:
        await asyncio.to_thread(
            engine.retrieval.process_file,
            save_path
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to index file: {str(e)}"
        )

    return {
        "status": "success",
        "filename": filename,
        "file_type": ext,
        "active_documents": engine.retrieval.active_documents,
        "vector_count": (
            engine.retrieval.pdf_vectordb.index.ntotal
            if engine.retrieval.pdf_vectordb
            else 0
        )
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint — intelligent intent routing + hybrid retrieval.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty"
        )

    result = await engine.process_query(
        query=request.query.strip(),
        history=request.history or []
    )

    return ChatResponse(
        answer=result.get("answer", ""),
        intent=result.get("intent", "general"),
        rewritten_query=result.get("rewritten_query", request.query),
        reasoning=result.get("reasoning", ""),
        execution_plan=result.get("execution_plan", {}),
        sources=result.get("sources", []),
        retrieved_chunks=result.get("retrieved_chunks", [])
    )


@app.get("/documents")
async def get_documents():
    return {
        "documents": engine.retrieval.active_documents,
        "vector_count": (
            engine.retrieval.pdf_vectordb.index.ntotal
            if engine.retrieval.pdf_vectordb
            else 0
        )
    }


@app.delete("/documents")
async def clear_documents():
    try:
        await asyncio.to_thread(engine.retrieval.clear_documents)
        return {"status": "success", "message": "All documents cleared"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear documents: {str(e)}"
        )