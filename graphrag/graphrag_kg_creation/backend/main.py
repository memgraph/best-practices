import os
import logging
import shutil
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx

# Add the ai-toolkit path to sys.path for imports
import sys
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
AI_TOOLKIT_DIR = os.path.join(SCRIPT_DIR, "ai-toolkit")
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "unstructured2graph", "src"))
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "integrations", "lightrag-memgraph", "src"))
sys.path.insert(0, os.path.join(AI_TOOLKIT_DIR, "memgraph-toolbox", "src"))

from lightrag_memgraph import MemgraphLightRAGWrapper
from memgraph_toolbox.api.memgraph import Memgraph
from unstructured2graph import from_unstructured, create_index, make_chunks, create_vector_search_index, compute_embeddings

load_dotenv()

app = FastAPI(title="GraphRAG KG Creation API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LIGHTRAG_DIR = os.path.join(SCRIPT_DIR, "lightrag_storage.out")

# Global variables for shared resources
_lightrag_wrapper = None
_memgraph = None


async def initialize_resources(cleanup: bool = False, create_vector_index: bool = False):
    """Initialize Memgraph and LightRAG wrapper if not already initialized."""
    global _lightrag_wrapper, _memgraph
    
    if _memgraph is None:
        _memgraph = Memgraph()
        
        if cleanup:
            logger.info("Cleaning up existing data in Memgraph...")
            _memgraph.query("STORAGE MODE IN_MEMORY_ANALYTICAL")
            _memgraph.query("DROP GRAPH")
            _memgraph.query("STORAGE MODE IN_MEMORY_TRANSACTIONAL")
        
        # Create index for Chunk nodes
        create_index(_memgraph, "Chunk", "hash")
        
        if create_vector_index:
            create_vector_search_index(_memgraph, "Chunk", "embedding")
    
    if _lightrag_wrapper is None:
        # Setup LightRAG directory
        lightrag_log_file = os.path.join(LIGHTRAG_DIR, "lightrag.log")
        if cleanup:
            if os.path.exists(lightrag_log_file):
                os.remove(lightrag_log_file)
            if os.path.exists(LIGHTRAG_DIR):
                shutil.rmtree(LIGHTRAG_DIR)
        if not os.path.exists(LIGHTRAG_DIR):
            os.mkdir(LIGHTRAG_DIR)
        
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


@app.get("/")
async def root():
    return {"message": "GraphRAG KG Creation API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/ingest")
async def ingest_documents(request: Request):
    """
    Ingest unstructured documents from URLs into Memgraph using unstructured2graph.
    
    Expected JSON body:
    {
        "urls": ["url1", "url2", ...],
        "only_chunks": false,
        "link_chunks": true,
        "create_vector_index": true,
        "cleanup": true
    }
    """
    # Parse request body
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    
    # Extract parameters with defaults
    urls = body.get("urls", [])
    only_chunks = body.get("only_chunks", False)
    link_chunks = body.get("link_chunks", True)
    create_vector_index = body.get("create_vector_index", True)
    cleanup = body.get("cleanup", True)
    
    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key."
        )

    if not urls or not isinstance(urls, list):
        raise HTTPException(
            status_code=400,
            detail="No URLs provided. Please provide at least one URL in the 'urls' array."
        )

    try:
        logger.info(f"Processing {len(urls)} documentation pages. Starting ingestion...")

        memgraph, lightrag_wrapper = await initialize_resources(cleanup=cleanup)

        # Ingest documents
        await from_unstructured(
            urls,
            memgraph,
            lightrag_wrapper,
            only_chunks=only_chunks,
            link_chunks=link_chunks,
        )

        # Create vector index and compute embeddings if requested
        if create_vector_index:
            logger.info("Creating vector search index and computing embeddings...")
            try:
                compute_embeddings(memgraph, "Chunk")
                logger.info("Successfully created vector index and computed embeddings")
            except Exception as e:
                logger.warning(f"Error creating vector index or computing embeddings: {str(e)}")

        logger.info("Successfully ingested all documentation pages into Memgraph!")

        return {
            "message": "Successfully ingested all documentation pages into Memgraph!",
            "urls_processed": len(urls),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during ingestion: {str(e)}"
        )


@app.post("/ingest/single")
async def ingest_single_document(request: Request):
    """
    Ingest a single document from a URL into Memgraph.
    Useful for progress tracking - process one document at a time.
    
    Expected JSON body:
    {
        "url": "https://example.com/doc",
        "only_chunks": false,
        "link_chunks": true,
        "create_vector_index": true,
        "cleanup": false  # Usually false for single document ingestion
    }
    """
    # Parse request body
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    
    # Extract parameters with defaults
    url = body.get("url")
    only_chunks = body.get("only_chunks", False)
    link_chunks = body.get("link_chunks", True)
    create_vector_index = body.get("create_vector_index", True)
    cleanup = body.get("cleanup", False)
    
    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key."
        )

    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=400,
            detail="No URL provided. Please provide a 'url' string."
        )

    try:
        logger.info(f"Processing single document: {url}")

        memgraph, lightrag_wrapper = await initialize_resources(cleanup=cleanup)

        # Ingest single document
        await from_unstructured(
            [url],
            memgraph,
            lightrag_wrapper,
            only_chunks=only_chunks,
            link_chunks=link_chunks,
        )

        # Create vector index and compute embeddings if requested
        if create_vector_index:
            logger.info("Computing embeddings and creating vector search index...")
            try:
                # Compute embeddings for all chunks (including newly added ones)
                compute_embeddings(memgraph, "Chunk")
                logger.info("Successfully computed embeddings and created vector index")
            except Exception as e:
                logger.warning(f"Error computing embeddings or creating vector index: {str(e)}")

        logger.info(f"Successfully ingested document: {url}")

        return {
            "message": f"Successfully ingested document: {url}",
            "url": url,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during ingestion: {str(e)}"
        )


@app.post("/ingest/estimate")
async def estimate_ingestion(request: Request):
    """
    Estimate the number of chunks and processing time for given URLs.
    Returns chunk count per document and total estimated time (10 seconds per chunk).
    
    Expected JSON body:
    {
        "urls": ["url1", "url2", ...]
    }
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    
    urls = body.get("urls", [])
    
    if not urls or not isinstance(urls, list):
        raise HTTPException(
            status_code=400,
            detail="No URLs provided. Please provide at least one URL in the 'urls' array."
        )
    
    try:
        # Get chunk estimates without full processing
        chunked_documents = make_chunks(urls)
        
        estimates = []
        total_chunks = 0
        
        for doc in chunked_documents:
            chunk_count = len(doc.chunks)
            total_chunks += chunk_count
            estimated_time = chunk_count * 10  # 10 seconds per chunk
            
            estimates.append({
                "url": str(doc.source),
                "chunk_count": chunk_count,
                "estimated_time_seconds": estimated_time
            })
        
        total_estimated_time = total_chunks * 10
        
        return {
            "total_chunks": total_chunks,
            "total_estimated_time_seconds": total_estimated_time,
            "documents": estimates
        }
    
    except Exception as e:
        logger.error(f"Error estimating ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error estimating ingestion: {str(e)}"
        )


@app.post("/query")
async def query_graph(request: Request):
    """
    Query the knowledge graph with a natural language question.
    Uses mcp-memgraph service to execute queries.
    
    Expected JSON body:
    {
        "question": "What is Memgraph?"
    }
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    
    question = body.get("question", "")
    
    if not question or not isinstance(question, str):
        raise HTTPException(
            status_code=400,
            detail="No question provided. Please provide a 'question' string."
        )
    
    # MCP service URL - use service name when running in Docker, localhost when running locally
    # Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
    mcp_url = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp/")
    
    try:
        # For now, create a simple Cypher query that searches for nodes containing keywords from the question
        # This is a basic implementation - in production, you'd use an LLM to generate better Cypher queries
        question_lower = question.lower()
        keywords = [word for word in question_lower.split() if len(word) > 3 and word.isalnum()]
        
        # Build a simple query to find relevant nodes
        # Search in Chunk nodes (text content) and base nodes (entities)
        if keywords:
            # Sanitize keyword - remove any single quotes and escape
            first_keyword = keywords[0].replace("'", "").replace('"', '')[:50]  # Limit length
            # Create a query that searches for chunks containing the keywords
            cypher_query = f"""
            MATCH (n)
            WHERE (n:Chunk AND toLower(n.text) CONTAINS '{first_keyword}')
               OR (n:base AND toLower(n.name) CONTAINS '{first_keyword}')
            RETURN n
            LIMIT 10
            """
        else:
            # Fallback query - just return some nodes
            cypher_query = "MATCH (n:Chunk) RETURN n LIMIT 10"
        
        # Call mcp-memgraph service to execute the query
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "run_query",
                "arguments": {
                    "query": cypher_query.strip()
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                mcp_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            mcp_result = response.json()
            
            # Extract the result from MCP response
            if "result" in mcp_result and "content" in mcp_result["result"]:
                query_results = mcp_result["result"]["content"]
                if isinstance(query_results, list) and len(query_results) > 0:
                    # Format the results into a readable answer
                    result_count = len(query_results)
                    answer = f"Found {result_count} result(s) related to your question: '{question}'.\n\n"
                    answer += "Query results:\n"
                    for i, result in enumerate(query_results[:5], 1):  # Show first 5 results
                        if isinstance(result, dict):
                            answer += f"\n{i}. {json.dumps(result, indent=2)}\n"
                    if result_count > 5:
                        answer += f"\n... and {result_count - 5} more result(s)."
                else:
                    answer = f"No results found for your question: '{question}'. The graph might not contain relevant information yet."
            else:
                # Fallback if response format is different
                answer = f"Query executed successfully. Response: {json.dumps(mcp_result, indent=2)}"
            
            return {
                "question": question,
                "answer": answer,
                "status": "success",
                "mcp_response": mcp_result
            }
            
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to mcp-memgraph at {mcp_url}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to mcp-memgraph service. Make sure the service is running. Error: {str(e)}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from mcp-memgraph: {str(e)}")
        error_detail = f"Error from mcp-memgraph service: {str(e)}"
        if e.response.text:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", error_detail)
            except:
                error_detail = e.response.text[:200]
        raise HTTPException(
            status_code=e.response.status_code,
            detail=error_detail
        )
    except Exception as e:
        logger.error(f"Error querying graph: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error querying graph: {str(e)}"
        )


@app.get("/stats")
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


@app.get("/mcp/test")
async def test_mcp_memgraph():
    """
    Dummy API endpoint to test calling the mcp-memgraph service.
    Calls the get_schema tool from mcp-memgraph.
    """
    # MCP service URL - use service name when running in Docker, localhost when running locally
    # Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
    mcp_url = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp/")
    
    try:
        # MCP uses JSON-RPC format for streamable-http transport
        # Call the get_schema tool
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_schema",
                "arguments": {}
            }
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                mcp_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "status": "success",
                "mcp_url": mcp_url,
                "mcp_response": result
            }
            
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to mcp-memgraph at {mcp_url}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to mcp-memgraph service at {mcp_url}. Make sure the service is running."
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from mcp-memgraph: {str(e)}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error from mcp-memgraph service: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error calling mcp-memgraph: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error calling mcp-memgraph: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

