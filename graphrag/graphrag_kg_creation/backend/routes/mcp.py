"""
MCP (Model Context Protocol) test endpoints.
"""
import os
import logging
import sys
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import call_mcp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])

# MCP service URL - use service name when running in Docker, localhost when running locally
# Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
MCP_URL = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")


@router.get("/test")
async def test_mcp_memgraph():
    """
    Dummy API endpoint to test calling the mcp-memgraph service.
    Calls the get_schema tool from mcp-memgraph.
    """
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
        
        result = await call_mcp_service(MCP_URL, payload, timeout=10.0)
        
        return {
            "status": "success",
            "mcp_url": MCP_URL,
            "mcp_response": result
        }
            
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to mcp-memgraph at {MCP_URL}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to mcp-memgraph service at {MCP_URL}. Make sure the service is running."
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


@router.get("/tools")
async def list_mcp_tools():
    """
    List all available tools from the mcp-memgraph service.
    Uses the tools/list method from MCP JSON-RPC.
    """
    try:
        # MCP uses JSON-RPC format for streamable-http transport
        # Call the tools/list method
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        result = await call_mcp_service(MCP_URL, payload, timeout=10.0)
        
        # Extract tools from the response
        tools = []
        if "result" in result and "tools" in result["result"]:
            tools = result["result"]["tools"]
        
        return {
            "status": "success",
            "mcp_url": MCP_URL,
            "tools": tools,
            "mcp_response": result
        }
            
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to mcp-memgraph at {MCP_URL}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to mcp-memgraph service at {MCP_URL}. Make sure the service is running."
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from mcp-memgraph: {str(e)}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error from mcp-memgraph service: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error listing mcp-memgraph tools: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing mcp-memgraph tools: {str(e)}"
        )


class CallToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


@router.post("/call")
async def call_mcp_tool(request: CallToolRequest):
    """
    Call a specific MCP tool with provided arguments.
    """
    try:
        # MCP uses JSON-RPC format for streamable-http transport
        # Call the specified tool with provided arguments
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": request.tool_name,
                "arguments": request.arguments
            }
        }
        
        result = await call_mcp_service(MCP_URL, payload, timeout=30.0)
        
        # Extract the result content
        content = None
        if "result" in result and "content" in result["result"]:
            content = result["result"]["content"]
        
        return {
            "status": "success",
            "mcp_url": MCP_URL,
            "tool_name": request.tool_name,
            "arguments": request.arguments,
            "result": content,
            "mcp_response": result
        }
            
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to mcp-memgraph at {MCP_URL}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to mcp-memgraph service at {MCP_URL}. Make sure the service is running."
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
        logger.error(f"Error calling mcp-memgraph tool: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error calling mcp-memgraph tool: {str(e)}"
        )

