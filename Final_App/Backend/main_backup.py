from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from rag_handler import RAGHandler
from ai_handler import AIHandler
from sendData import stream_router
from databricks_analytics import analytics_router
from ml_router import ml_router
from live_data_injection_pipeline.stream_router import pipeline_router
from live_data_injection_pipeline.stream_engine import start_engine
from ml_handler import get_ml_handler

load_dotenv()

app = FastAPI(
    title="AI RAG API",
    description="FastAPI application for AI responses and RAG using Multi-Model LLM (Gemini + OpenAI)",
    version="2.0.0"
)

# ---------------------------------------------------------------------------
# CORS — allow the frontend origins
# ---------------------------------------------------------------------------
frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080,http://localhost:8081,http://127.0.0.1:8081,http://localhost:8082,http://127.0.0.1:8082,http://localhost:8083,http://127.0.0.1:8083",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize handlers. RAG is loaded lazily because the dashboard does not need
# embeddings, and first-time model loading may require network access.
rag_handler: RAGHandler | None = None
ai_handler: AIHandler | None = None


def get_rag_handler() -> RAGHandler:
    global rag_handler
    if rag_handler is None:
        rag_handler = RAGHandler()
    return rag_handler


def get_ai_handler() -> AIHandler:
    global ai_handler
    if ai_handler is None:
        ai_handler = AIHandler()  # Multi-model: Gemini (primary) + OpenAI (fallback)
    return ai_handler

# Models
class QueryRequest(BaseModel):
    query: str
    use_rag: bool = True
    top_k: int = 3

class QueryResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None
    confidence: Optional[float] = None

class DocumentUploadResponse(BaseModel):
    message: str
    documents_count: int

# Routes
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "message": "AI RAG API is running",
        "status": "healthy",
        "version": "1.0.0",
        "databricks_status_endpoint": "GET /api/databricks-status",
    }

app.include_router(stream_router, prefix="/api/stream", tags=["Streaming"])
app.include_router(analytics_router, tags=["Databricks Analytics"])
app.include_router(ml_router)
app.include_router(pipeline_router)

# Mount Gradio ML Demo Interface at /model/test
import sys
import gradio as gr

_models_repo_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "supply-chain-ml-models"
)
if _models_repo_path not in sys.path:
    sys.path.insert(0, _models_repo_path)

try:
    from app import demo as gradio_demo
    app = gr.mount_gradio_app(app, gradio_demo, path="/model/test")
    print("[main] Successfully mounted Gradio ML app at /model/test")
except Exception as e:
    print(f"[main] Failed to mount Gradio app at /model/test: {e}")



@app.on_event("startup")
async def _start_live_pipeline():
    """Start the live data injection pipeline on server boot."""
    try:
        handler = get_ml_handler()
        if handler.is_loaded:
            start_engine(handler)
        else:
            print("[main] ML models not loaded — pipeline will not start.")
    except Exception as e:
        print(f"[main] Pipeline startup error: {e}")

@app.post("/query", response_model=QueryResponse, tags=["AI Queries"])
async def query(request: QueryRequest):
    """
    Process a query with optional RAG.
    
    - **query**: The input query string
    - **use_rag**: Whether to use RAG for retrieval (default: True)
    - **top_k**: Number of top documents to retrieve (default: 3)
    """
    try:
        if request.use_rag:
            handler = get_rag_handler()
            # Retrieve relevant documents from vector store
            relevant_docs = handler.retrieve(request.query, top_k=request.top_k)
            assistant = get_ai_handler()
            
            # Generate response using retrieved context
            response, confidence = assistant.generate_response(
                query=request.query,
                context=relevant_docs
            )
            
            # Extract sources
            sources = [doc.get("source", "Unknown") for doc in relevant_docs]
            
            return QueryResponse(
                response=response,
                sources=sources,
                confidence=confidence
            )
        else:
            assistant = get_ai_handler()
            # Generate response without RAG
            response, confidence = assistant.generate_response(query=request.query)
            
            return QueryResponse(
                response=response,
                confidence=confidence
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-documents", response_model=DocumentUploadResponse, tags=["Document Management"])
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload documents for RAG indexing.
    Supports .txt, .pdf, and .md files.
    """
    try:
        documents = []
        
        for file in files:
            content = await file.read()
            
            # Simple text extraction (extend for PDF support)
            if file.filename.endswith(('.txt', '.md')):
                text = content.decode('utf-8')
                documents.append({
                    "content": text,
                    "source": file.filename
                })
        
        if not documents:
            raise HTTPException(status_code=400, detail="No valid documents provided")
        
        # Add documents to vector store
        count = get_rag_handler().add_documents(documents)
        
        return DocumentUploadResponse(
            message="Documents uploaded and indexed successfully",
            documents_count=count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear-documents", tags=["Document Management"])
async def clear_documents():
    """Clear all documents from the vector store"""
    try:
        get_rag_handler().clear()
        return {"message": "Vector store cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents-status", tags=["Document Management"])
async def get_documents_status():
    """Get the status of stored documents"""
    try:
        status = get_rag_handler().get_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
