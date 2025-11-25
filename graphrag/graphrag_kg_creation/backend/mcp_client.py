"""
MCP (Model Context Protocol) client for communicating with mcp-memgraph service.
Handles SSE parsing, session management, and initialization.
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
    """
    Parse Server-Sent Events (SSE) format response from MCP streamable-http.
    Format: event: <event-type>\ndata: <json-data>\n\n
    """
    if not text or not text.strip():
        raise ValueError("Empty SSE response")
    
    # Check if it's SSE format
    if "event:" in text or "data:" in text:
        lines = text.split('\n')
        json_data = None
        
        for i, line in enumerate(lines):
            if line.startswith('data:'):
                # Extract JSON data after "data: "
                data_str = line[5:].strip()  # Remove "data: " prefix
                if data_str:
                    try:
                        json_data = json.loads(data_str)
                        break
                    except json.JSONDecodeError:
                        # Try to find JSON in the line
                        continue
        
        if json_data is None:
            # Try to find JSON anywhere in the response
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
        # Not SSE format, try to parse as plain JSON
        return json.loads(text)


async def initialize_mcp_session(mcp_url: str, timeout: float = 10.0) -> None:
    """
    Initialize MCP session by sending an initialize request.
    This must be called before making any tool calls.
    """
    global _mcp_session_id, _mcp_initialized
    
    if _mcp_initialized and _mcp_session_id:
        return  # Already initialized
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # Send initialize request
        init_payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "graphrag-backend",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await client.post(mcp_url, json=init_payload, headers=headers)
        
        # Extract session ID from response headers
        if "mcp-session-id" in response.headers:
            _mcp_session_id = response.headers["mcp-session-id"]
            _mcp_initialized = True
            logger.info(f"MCP session initialized with ID: {_mcp_session_id}")
        else:
            # Try to get session ID from error response (some servers send it even on errors)
            if "mcp-session-id" in response.headers:
                _mcp_session_id = response.headers["mcp-session-id"]
            
            # Check if initialization was successful
            if response.status_code == 200:
                _mcp_initialized = True
            else:
                # Try to parse error
                try:
                    error_data = parse_sse_response(response.text) if response.text else {}
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    logger.warning(f"MCP initialization returned status {response.status_code}: {error_msg}")
                except:
                    pass


async def call_mcp_service(mcp_url: str, payload: dict, timeout: float = 30.0) -> dict:
    """
    Helper function to call MCP service with session management.
    Handles session ID extraction and inclusion for streamable-http transport.
    Parses SSE (Server-Sent Events) format responses.
    Automatically initializes the session if needed.
    """
    global _mcp_session_id, _mcp_initialized
    
    # Ensure session is initialized
    if not _mcp_initialized or not _mcp_session_id:
        await initialize_mcp_session(mcp_url, timeout=timeout)
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # Always include session ID
        if _mcp_session_id:
            headers["mcp-session-id"] = _mcp_session_id
        
        response = await client.post(mcp_url, json=payload, headers=headers)
        
        # Extract session ID from response headers (in case it changed)
        if "mcp-session-id" in response.headers:
            _mcp_session_id = response.headers["mcp-session-id"]
        
        # If we got a "Missing session ID" error, try to re-initialize
        if response.status_code == 400:
            try:
                error_data = parse_sse_response(response.text) if response.text else {}
                error_message = error_data.get("error", {}).get("message", "")
                if "Missing session ID" in error_message or "No valid session ID" in error_message or "before initialization" in error_message.lower():
                    # Reset and re-initialize
                    _mcp_initialized = False
                    _mcp_session_id = None
                    await initialize_mcp_session(mcp_url, timeout=timeout)
                    
                    # Retry the request with new session ID
                    if _mcp_session_id:
                        headers["mcp-session-id"] = _mcp_session_id
                        response = await client.post(mcp_url, json=payload, headers=headers)
                        if "mcp-session-id" in response.headers:
                            _mcp_session_id = response.headers["mcp-session-id"]
            except (json.JSONDecodeError, ValueError):
                pass  # Continue with original error handling
        
        # Check response status before parsing
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Try to parse error from SSE or JSON format
            try:
                error_data = parse_sse_response(e.response.text) if e.response.text else {}
                error_message = error_data.get("error", {}).get("message", str(error_data))
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error from MCP service: {error_message}"
                )
            except (json.JSONDecodeError, ValueError) as parse_err:
                # If we can't parse, use the response text
                error_text = e.response.text[:500] if e.response.text else "Unknown error"
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error from MCP service (status {e.response.status_code}): {error_text}"
                )
        
        # Check if response has content
        if not response.text or response.text.strip() == "":
            raise HTTPException(
                status_code=500,
                detail="Empty response from MCP service"
            )
        
        # Parse response (SSE or JSON format)
        try:
            return parse_sse_response(response.text)
        except (json.JSONDecodeError, ValueError) as e:
            # Log the actual response for debugging
            logger.error(f"Failed to parse response from MCP service. Status: {response.status_code}, Content-Type: {response.headers.get('content-type')}, Body: {response.text[:500]}")
            raise HTTPException(
                status_code=500,
                detail=f"Invalid response from MCP service: {str(e)}. Response: {response.text[:200]}"
            )

