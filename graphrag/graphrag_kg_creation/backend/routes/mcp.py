"""
MCP (Model Context Protocol) test endpoints.
"""
import os
import logging
import sys
import httpx
from fastapi import APIRouter, HTTPException

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import call_mcp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/test")
async def test_mcp_memgraph():
    """
    Dummy API endpoint to test calling the mcp-memgraph service.
    Calls the get_schema tool from mcp-memgraph.
    """
    # MCP service URL - use service name when running in Docker, localhost when running locally
    # Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
    mcp_url = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")
    
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
        
        result = await call_mcp_service(mcp_url, payload, timeout=10.0)
        
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

