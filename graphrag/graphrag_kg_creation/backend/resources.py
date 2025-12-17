"""
Resource management for Memgraph and LightRAG wrapper.
Handles initialization and cleanup of database connections and wrappers.
"""
import os
import shutil
import logging
import sys

# Add the ai-toolkit path to sys.path for imports
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
AI_TOOLKIT_DIR = os.path.join(SCRIPT_DIR, "ai-toolkit")
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "unstructured2graph", "src"))
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "integrations", "lightrag-memgraph", "src"))
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "memgraph-toolbox", "src"))

from lightrag_memgraph import MemgraphLightRAGWrapper
from memgraph_toolbox.api.memgraph import Memgraph
from unstructured2graph import create_index, create_vector_search_index

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LIGHTRAG_DIR = os.path.join(SCRIPT_DIR, "lightrag_storage.out")

# Global variables for shared resources
_lightrag_wrapper = None
_memgraph = None


async def initialize_resources(cleanup: bool = False, create_vector_index: bool = False):
    """Initialize Memgraph and LightRAG wrapper. Always creates fresh instances from scratch."""
    global _lightrag_wrapper, _memgraph
    
    # Always cleanup existing LightRAG wrapper if it exists
    if _lightrag_wrapper is not None:
        try:
            await _lightrag_wrapper.afinalize()
        except Exception as e:
            logger.warning(f"Error finalizing existing LightRAG wrapper: {str(e)}")
        _lightrag_wrapper = None
    
    # Always create a new Memgraph instance (don't reuse existing)
    _memgraph = Memgraph()
    
    # Always cleanup Memgraph data if requested
    if cleanup:
        logger.info("Cleaning up existing data in Memgraph...")
        try:
            _memgraph.query("STORAGE MODE IN_MEMORY_ANALYTICAL")
            _memgraph.query("DROP GRAPH")
            _memgraph.query("STORAGE MODE IN_MEMORY_TRANSACTIONAL")
        except Exception as e:
            logger.warning(f"Error during Memgraph cleanup: {str(e)}")
    
    # Always create index for Chunk nodes (will fail gracefully if already exists)
    try:
        create_index(_memgraph, "Chunk", "hash")
    except Exception as e:
        logger.warning(f"Error creating index (may already exist): {str(e)}")
    
    if create_vector_index:
        try:
            create_vector_search_index(_memgraph, "Chunk", "embedding")
        except Exception as e:
            logger.warning(f"Error creating vector index (may already exist): {str(e)}")
    
    # Always setup LightRAG directory from scratch
    lightrag_log_file = os.path.join(LIGHTRAG_DIR, "lightrag.log")
    if cleanup:
        # Cleanup existing LightRAG files
        if os.path.exists(lightrag_log_file):
            try:
                os.remove(lightrag_log_file)
            except Exception as e:
                logger.warning(f"Error removing log file: {str(e)}")
        if os.path.exists(LIGHTRAG_DIR):
            try:
                shutil.rmtree(LIGHTRAG_DIR)
            except Exception as e:
                logger.warning(f"Error removing LightRAG directory: {str(e)}")
    
    # Ensure LightRAG directory exists
    if not os.path.exists(LIGHTRAG_DIR):
        os.makedirs(LIGHTRAG_DIR, exist_ok=True)
    
    # Always create a new LightRAG wrapper instance
    _lightrag_wrapper = MemgraphLightRAGWrapper(
        log_level="WARNING",
        disable_embeddings=True
    )
    await _lightrag_wrapper.initialize(working_dir=LIGHTRAG_DIR)
    
    return _memgraph, _lightrag_wrapper


async def cleanup_resources():
    """Cleanup resources if needed."""
    global _lightrag_wrapper
    if _lightrag_wrapper is not None:
        await _lightrag_wrapper.afinalize()
        _lightrag_wrapper = None

