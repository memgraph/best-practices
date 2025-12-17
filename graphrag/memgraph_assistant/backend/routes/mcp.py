"""
MCP (Model Context Protocol) test endpoints.
"""
import os
import logging
import sys
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import call_mcp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])

# MCP service URL
MCP_URL = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")


@router.get("/test")
async def test_mcp_memgraph():
    """Test calling the mcp-memgraph service."""
    try:
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
    except Exception as e:
        logger.error(f"Error calling mcp-memgraph: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error calling mcp-memgraph: {str(e)}"
        )


@router.get("/tools")
async def list_mcp_tools():
    """List all available tools from the mcp-memgraph service."""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        result = await call_mcp_service(MCP_URL, payload, timeout=10.0)
        
        tools = []
        if "result" in result and "tools" in result["result"]:
            tools = result["result"]["tools"]
        
        return {
            "status": "success",
            "mcp_url": MCP_URL,
            "tools": tools,
            "mcp_response": result
        }
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
    """Call a specific MCP tool with provided arguments."""
    try:
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
    except Exception as e:
        logger.error(f"Error calling mcp-memgraph tool: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error calling mcp-memgraph tool: {str(e)}"
        )

