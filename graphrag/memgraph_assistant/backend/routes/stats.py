"""
Statistics endpoints for querying knowledge graph statistics.
"""
import logging
import sys
import os
from fastapi import APIRouter, HTTPException

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add the ai-toolkit path to sys.path for imports
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
AI_TOOLKIT_DIR = os.path.join(SCRIPT_DIR, "ai-toolkit")
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "memgraph-toolbox", "src"))

from memgraph_toolbox.api.memgraph import Memgraph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("")
async def get_stats():
    """
    Get statistics about the ingested data in Memgraph.
    """
    try:
        memgraph = Memgraph()

        # Get chunk count
        chunk_result = memgraph.query("MATCH (n:Chunk) RETURN count(n) as count")
        chunk_count = chunk_result[0]["count"] if chunk_result else 0

        # Get entity count (base nodes from LightRAG)
        entity_result = memgraph.query("MATCH (n:base) RETURN count(n) as count")
        entity_count = entity_result[0]["count"] if entity_result else 0

        # Get relationship count
        rel_result = memgraph.query("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = rel_result[0]["count"] if rel_result else 0

        # Get total node count
        node_result = memgraph.query("MATCH (n) RETURN count(n) as count")
        node_count = node_result[0]["count"] if node_result else 0

        return {
            "chunks": chunk_count,
            "entities": entity_count,
            "relationships": rel_count,
            "nodes": node_count
        }

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting stats: {str(e)}"
        )

