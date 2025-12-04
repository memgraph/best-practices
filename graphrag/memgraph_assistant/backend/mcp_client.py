"""
MCP (Model Context Protocol) client for communicating with mcp-memgraph service.
"""
import os
import json
import re
import logging
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Module-level session ID storage for MCP streamable-http
_mcp_session_id = None
_mcp_initialized = False


def parse_sse_response(text: str) -> dict:
    """Parse Server-Sent Events (SSE) format response from MCP streamable-http."""
    if not text or not text.strip():
        raise ValueError("Empty SSE response")
    
    if "event:" in text or "data:" in text:
        lines = text.split('\n')
        json_data = None
        
        for i, line in enumerate(lines):
            if line.startswith('data:'):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        json_data = json.loads(data_str)
                        break
                    except json.JSONDecodeError:
                        continue
        
        if json_data is None:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    json_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        if json_data is None:
            raise ValueError(f"Could not extract JSON from SSE response: {text[:200]}")
        
        return json_data
    else:
        return json.loads(text)


async def initialize_mcp_session(mcp_url: str, timeout: float = 10.0) -> None:
    """Initialize MCP session by sending an initialize request."""
    global _mcp_session_id, _mcp_initialized
    
    if _mcp_initialized and _mcp_session_id:
        return
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        init_payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "memgraph-assistant-backend",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await client.post(mcp_url, json=init_payload, headers=headers)
        
        if "mcp-session-id" in response.headers:
            _mcp_session_id = response.headers["mcp-session-id"]
            _mcp_initialized = True
            logger.info(f"MCP session initialized with ID: {_mcp_session_id}")


async def call_mcp_service(mcp_url: str, payload: dict, timeout: float = 60.0) -> dict:
    """Helper function to call MCP service with session management."""
    global _mcp_session_id, _mcp_initialized
    
    if not _mcp_initialized or not _mcp_session_id:
        await initialize_mcp_session(mcp_url, timeout=timeout)
    
    timeout_config = httpx.Timeout(timeout, connect=10.0, read=timeout)
    
    async with httpx.AsyncClient(timeout=timeout_config, follow_redirects=True) as client:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        if _mcp_session_id:
            headers["mcp-session-id"] = _mcp_session_id
        
        response = await client.post(mcp_url, json=payload, headers=headers)
        
        if "mcp-session-id" in response.headers:
            _mcp_session_id = response.headers["mcp-session-id"]
        
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            try:
                error_data = parse_sse_response(e.response.text) if e.response.text else {}
                error_message = error_data.get("error", {}).get("message", str(error_data))
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error from MCP service: {error_message}"
                )
            except (json.JSONDecodeError, ValueError):
                error_text = e.response.text[:500] if e.response.text else "Unknown error"
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error from MCP service (status {e.response.status_code}): {error_text}"
                )
        
        if not response.text or response.text.strip() == "":
            raise HTTPException(
                status_code=500,
                detail=f"Empty response from MCP service (status {response.status_code})"
            )
        
        try:
            return parse_sse_response(response.text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse response from MCP service: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Invalid response from MCP service: {str(e)}"
            )

