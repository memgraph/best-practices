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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


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
    
    # MCP service URL - use service name when running in Docker, localhost when running locally
    # Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
    mcp_url = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")
    
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
        
        mcp_result = await call_mcp_service(mcp_url, payload, timeout=30.0)
        
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

