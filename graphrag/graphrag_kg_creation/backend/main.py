"""
Main FastAPI application entry point.
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
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="GraphRAG KG Creation API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routes
from routes import ingest, query, stats, mcp

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(stats.router)
app.include_router(mcp.router)

# Import OpenAI Agents router if available (requires openai-agents package)
try:
    from routes import openai_agents
    app.include_router(openai_agents.router)
except ImportError:
    logger.warning("OpenAI Agents router not available. Install openai-agents package to enable.")

# Import OpenAI Agents With Planning router (multi-agent orchestration with planner-executor pattern)
try:
    from routes import openai_agents_with_planning
    app.include_router(openai_agents_with_planning.router)
except ImportError as e:
    logger.warning(f"OpenAI Agents With Planning router not available: {e}")


@app.get("/")
async def root():
    return {"message": "GraphRAG KG Creation API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

