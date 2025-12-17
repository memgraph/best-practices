"""
Query endpoints for querying the knowledge graph.
"""
import os
import json
import logging
import sys
import httpx
from fastapi import APIRouter, HTTPException, Request

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import call_mcp_service
from routes.llm_utils import generate_answer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

# MCP service URL - use service name when running in Docker, localhost when running locally
# Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
MCP_URL = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")


def remove_embeddings_from_response(data):
    """
    Recursively remove 'embedding' keys from dictionaries in the response.
    """
    if isinstance(data, dict):
        return {k: remove_embeddings_from_response(v) for k, v in data.items() if k != "embedding"}
    elif isinstance(data, list):
        return [remove_embeddings_from_response(item) for item in data]
    else:
        return data


@router.post("")
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
    
    try:
        # Use vector search to find relevant chunks based on question embedding
        # Sanitize the question to prevent Cypher injection - escape single quotes
        sanitized_question = question.replace("'", "\\'").replace("\\", "\\\\")
        
        # Build the GraphRAG query that embeds the prompt and searches for similar chunks
        cypher_query = f"""
        CALL embeddings.text(['{sanitized_question}']) YIELD embeddings, success
        CALL vector_search.search('vs_name', 5, embeddings[0]) YIELD distance, node, similarity
        MATCH (node)-[r*bfs]-(dst:Chunk)
        WITH DISTINCT dst, degree(dst) AS degree ORDER BY degree DESC
        RETURN dst LIMIT 5
        """
        
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
        
        mcp_result = await call_mcp_service(MCP_URL, payload, timeout=30.0)
        
        # Remove embedding from mcp_response before processing
        cleaned_mcp_response = remove_embeddings_from_response(mcp_result)
        
        # Extract structuredContent from MCP response
        structured_content = None
        if "result" in cleaned_mcp_response and "structuredContent" in cleaned_mcp_response["result"]:
            structured_content = cleaned_mcp_response["result"]["structuredContent"]
        
        if structured_content:
            # Generate answer using LLM
            answer = generate_answer(structured_content, question)
        else:
            answer = f"No results found for your question: '{question}'. The graph might not contain relevant information yet."
        
        return {
            "question": question,
            "answer": answer,
            "status": "success",
            "mcp_response": cleaned_mcp_response
        }
            
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to mcp-memgraph at {MCP_URL}: {str(e)}")
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

