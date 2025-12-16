"""
Knowledge graph construction functions for Memgraph documentation ingestion.
"""
import os
import sys
import logging
import shutil
from pathlib import Path
from typing import List

# Path setup for imports
SCRIPT_DIR = Path(__file__).parent.absolute()
AI_TOOLKIT_DIR = SCRIPT_DIR / "ai-toolkit"
UNSTRUCTURED2GRAPH_PATH = AI_TOOLKIT_DIR / "unstructured2graph" / "src"
LIGHTRAG_PATH = AI_TOOLKIT_DIR / "integrations" / "lightrag-memgraph" / "src"
MEMGRAPH_TOOLBOX_PATH = AI_TOOLKIT_DIR / "memgraph-toolbox" / "src"

sys.path.insert(0, str(UNSTRUCTURED2GRAPH_PATH))
sys.path.insert(0, str(LIGHTRAG_PATH))
sys.path.insert(0, str(MEMGRAPH_TOOLBOX_PATH))

from lightrag_memgraph import MemgraphLightRAGWrapper
from unstructured2graph import from_unstructured, create_index, create_vector_search_index
from memgraph_toolbox.api.memgraph import Memgraph

from database import check_url_processed, mark_url_processed

logger = logging.getLogger(__name__)


async def process_document(memgraph: Memgraph, lightrag_wrapper: MemgraphLightRAGWrapper, url: str):
    """Process a single document URL with LightRAG and unstructured2graph."""
    logger.info(f"Processing document: {url}")
    await from_unstructured([url], memgraph, lightrag_wrapper, only_chunks=False, link_chunks=True)
    logger.info(f"Successfully processed: {url}")


async def knowledge_graph_construction(
    memgraph: Memgraph,
    lightrag_wrapper: MemgraphLightRAGWrapper,
    urls: List[str],
    skip_processed: bool = False
) -> tuple[int, int, int]:
    """
    Construct knowledge graph by processing URLs with LightRAG and unstructured2graph.
    
    Returns:
        Tuple of (processed_count, skipped_count, error_count)
    """
    logger.info(f"Constructing knowledge graph from {len(urls)} URLs")
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for idx, url in enumerate(urls, 1):
        try:
            if skip_processed and check_url_processed(memgraph, url):
                logger.info(f"[{idx}/{len(urls)}] Skipping already processed: {url}")
                skipped_count += 1
                continue
            
            logger.info(f"[{idx}/{len(urls)}] Processing: {url}")
            await process_document(memgraph, lightrag_wrapper, url)
            mark_url_processed(memgraph, url)
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            error_count += 1
            continue
    
    return processed_count, skipped_count, error_count


async def initialize_memgraph_and_lightrag(cleanup: bool = False) -> tuple[Memgraph, MemgraphLightRAGWrapper]:
    """
    Initialize Memgraph connection and LightRAG wrapper.
    
    Args:
        cleanup: If True, drop all existing data
    
    Returns:
        Tuple of (Memgraph instance, LightRAG wrapper)
    """
    logger.info("Initializing Memgraph and LightRAG...")
    memgraph = Memgraph()
    
    if cleanup:
        logger.info("Cleaning up existing data...")
        try:
            memgraph.query("STORAGE MODE IN_MEMORY_ANALYTICAL")
            memgraph.query("DROP GRAPH")
            memgraph.query("STORAGE MODE IN_MEMORY_TRANSACTIONAL")
            logger.info("Successfully cleaned up existing data")
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
    
    try:
        create_index(memgraph, "Chunk", "hash")
        logger.info("Created index on Chunk(hash)")
    except Exception as e:
        logger.warning(f"Index may already exist: {str(e)}")
    
    try:
        create_vector_search_index(memgraph, "Chunk", "embedding")
        logger.info("Created vector search index on Chunk(embedding)")
    except Exception as e:
        logger.warning(f"Vector index may already exist: {str(e)}")
    
    text_indexes = [
        ("entity_id", "base", "entity_id"),
        ("text", "Chunk", "text"),
        ("query", "CypherQuery", "query"),
        ("url_description", "Url", "description, keywords"),
    ]
    
    for index_name, label, properties in text_indexes:
        try:
            memgraph.query(f"CREATE TEXT INDEX {index_name} ON :{label}({properties});")
            logger.info(f"Created text index {index_name} on {label}({properties})")
        except Exception as e:
            logger.warning(f"Text index {index_name} may already exist: {str(e)}")
    
    lightrag_dir = SCRIPT_DIR / "lightrag_storage.out"
    
    if cleanup and lightrag_dir.exists():
        try:
            shutil.rmtree(lightrag_dir)
            logger.info("Removed existing LightRAG directory")
        except Exception as e:
            logger.warning(f"Error removing LightRAG directory: {str(e)}")
    
    lightrag_dir.mkdir(exist_ok=True)
    
    lightrag_wrapper = MemgraphLightRAGWrapper(log_level="WARNING", disable_embeddings=True)
    await lightrag_wrapper.initialize(working_dir=str(lightrag_dir))
    
    logger.info("Successfully initialized Memgraph and LightRAG")
    return memgraph, lightrag_wrapper

