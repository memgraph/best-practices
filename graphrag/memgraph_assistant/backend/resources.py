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
from unstructured2graph import create_index, create_vector_search_index

# Import Memgraph after setting up path - we'll import it dynamically for main graph
# to allow setting environment variables before initialization
try:
    from memgraph_toolbox.api.memgraph import Memgraph
except ImportError:
    Memgraph = None

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LIGHTRAG_DIR = os.path.join(SCRIPT_DIR, "lightrag_storage.out")

# Global variables for shared resources
_lightrag_wrapper = None
_memgraph = None
_main_memgraph = None


async def initialize_resources(cleanup: bool = False, create_vector_index: bool = False, create_text_index: bool = True):
    """Initialize Memgraph and LightRAG wrapper."""
    global _lightrag_wrapper, _memgraph
    
    # Always cleanup existing LightRAG wrapper if it exists
    if _lightrag_wrapper is not None:
        try:
            await _lightrag_wrapper.afinalize()
        except Exception as e:
            logger.warning(f"Error finalizing existing LightRAG wrapper: {str(e)}")
        _lightrag_wrapper = None
    
    # Create Memgraph instance
    _memgraph = Memgraph()
    
    # Cleanup Memgraph data if requested
    if cleanup:
        logger.info("Cleaning up existing data in Memgraph...")
        try:
            _memgraph.query("STORAGE MODE IN_MEMORY_ANALYTICAL")
            _memgraph.query("DROP GRAPH")
            _memgraph.query("STORAGE MODE IN_MEMORY_TRANSACTIONAL")
        except Exception as e:
            logger.warning(f"Error during Memgraph cleanup: {str(e)}")
    
    # Create index for Chunk nodes
    try:
        create_index(_memgraph, "Chunk", "hash")
    except Exception as e:
        logger.warning(f"Error creating index (may already exist): {str(e)}")
    
    if create_vector_index:
        try:
            create_vector_search_index(_memgraph, "Chunk", "embedding")
        except Exception as e:
            logger.warning(f"Error creating vector index (may already exist): {str(e)}")
    
    if create_text_index:
        try:
            # Create text index for base entity_id
            _memgraph.query("CREATE TEXT INDEX entity_id ON :base(entity_id);")
            logger.info("Created text index on base(entity_id)")
        except Exception as e:
            logger.warning(f"Error creating text index on base(entity_id) (may already exist): {str(e)}")
        
        try:
            # Create text index for Chunk text
            _memgraph.query("CREATE TEXT INDEX text ON :Chunk(text);")
            logger.info("Created text index on Chunk(text)")
        except Exception as e:
            logger.warning(f"Error creating text index on Chunk(text) (may already exist): {str(e)}")
        
        try:
            # Create text index for CypherQuery query
            _memgraph.query("CREATE TEXT INDEX query ON :CypherQuery(query);")
            logger.info("Created text index on CypherQuery(query)")
        except Exception as e:
            logger.warning(f"Error creating text index on CypherQuery(query) (may already exist): {str(e)}")

        try:
            # Create text index for Url description
            _memgraph.query("CREATE TEXT INDEX url_description ON :Url(description, keywords);")
            logger.info("Created text index on Url(description, keywords)")
        except Exception as e:
            logger.warning(f"Error creating text index on Url(description, keywords) (may already exist): {str(e)}")
    
    # Setup LightRAG directory
    lightrag_log_file = os.path.join(LIGHTRAG_DIR, "lightrag.log")
    if cleanup:
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
    
    # Create LightRAG wrapper instance
    _lightrag_wrapper = MemgraphLightRAGWrapper(
        log_level="WARNING",
        disable_embeddings=True
    )
    await _lightrag_wrapper.initialize(working_dir=LIGHTRAG_DIR)
    
    return _memgraph, _lightrag_wrapper


async def initialize_main_graph():
    """Initialize separate Memgraph instance for user data (main graph)."""
    global _main_memgraph
    
    if _main_memgraph is None:
        # Import Memgraph here to ensure environment variables are set
        from memgraph_toolbox.api.memgraph import Memgraph
        
        # Store original environment variables
        original_host = os.environ.get('MEMGRAPH_HOST')
        original_port = os.environ.get('MEMGRAPH_PORT')
        
        # Set environment variables for main graph connection (port 7688)
        os.environ['MEMGRAPH_HOST'] = 'localhost'
        os.environ['MEMGRAPH_PORT'] = '7688'
        
        try:
            _main_memgraph = Memgraph()
            logger.info("Initialized main graph connection (port 7688)")
        except Exception as e:
            logger.error(f"Error initializing main graph: {e}")
            # Try without environment variables - Memgraph might use defaults
            _main_memgraph = Memgraph()
            logger.warning("Initialized main graph with default connection (may not be port 7688)")
        finally:
            # Restore original environment variables
            if original_host is not None:
                os.environ['MEMGRAPH_HOST'] = original_host
            else:
                os.environ.pop('MEMGRAPH_HOST', None)
                
            if original_port is not None:
                os.environ['MEMGRAPH_PORT'] = original_port
            else:
                os.environ.pop('MEMGRAPH_PORT', None)
    
    return _main_memgraph


def get_main_memgraph():
    """Get the main graph instance for user data."""
    global _main_memgraph
    if _main_memgraph is None:
        # Import Memgraph here to ensure environment variables are set
        from memgraph_toolbox.api.memgraph import Memgraph
        
        # Store original environment variables
        original_host = os.environ.get('MEMGRAPH_HOST')
        original_port = os.environ.get('MEMGRAPH_PORT')
        
        # Set environment variables for main graph connection (port 7688)
        os.environ['MEMGRAPH_HOST'] = 'localhost'
        os.environ['MEMGRAPH_PORT'] = '7688'
        
        try:
            _main_memgraph = Memgraph()
            logger.info("Initialized main graph connection (port 7688)")
        except Exception as e:
            logger.error(f"Error initializing main graph: {e}")
            # Try without environment variables - Memgraph might use defaults
            _main_memgraph = Memgraph()
            logger.warning("Initialized main graph with default connection (may not be port 7688)")
        finally:
            # Restore original environment variables
            if original_host is not None:
                os.environ['MEMGRAPH_HOST'] = original_host
            else:
                os.environ.pop('MEMGRAPH_HOST', None)
                
            if original_port is not None:
                os.environ['MEMGRAPH_PORT'] = original_port
            else:
                os.environ.pop('MEMGRAPH_PORT', None)
    return _main_memgraph


async def cleanup_resources():
    """Cleanup resources if needed."""
    global _lightrag_wrapper, _main_memgraph
    if _lightrag_wrapper is not None:
        await _lightrag_wrapper.afinalize()
        _lightrag_wrapper = None
    # Note: We don't close _main_memgraph connection as it's managed by the client
    _main_memgraph = None

