"""
Main FastAPI application entry point for Memgraph Assistant.
"""
import os
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add the ai-toolkit path to sys.path for imports
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
AI_TOOLKIT_DIR = os.path.join(SCRIPT_DIR, "ai-toolkit")
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "unstructured2graph", "src"))
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "integrations", "lightrag-memgraph", "src"))
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "memgraph-toolbox", "src"))

load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Memgraph Assistant API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routes
from routes import ingest, chat, mcp, stats, graph

# Include routers with /api prefix to match frontend proxy
app.include_router(ingest.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(mcp.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(graph.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Memgraph Assistant API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

