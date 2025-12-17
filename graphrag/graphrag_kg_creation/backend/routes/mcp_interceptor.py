"""
MCP Server interceptor for capturing tool calls.
This module provides a wrapper around MCP servers to intercept and log tool calls,
particularly useful for capturing run_query calls.
"""
import logging
import json
import traceback
import hashlib
from typing import List, Dict, Any, Optional, Callable, Awaitable
from agents.mcp.server import MCPServer
from .common import extract_structured_content

logger = logging.getLogger(__name__)


class InterceptingMCPServer(MCPServer):
    """
    Wrapper around an MCP server that intercepts tool calls to capture run_query calls.
    This allows us to track all Cypher queries executed during a request.
    Supports streaming callbacks for real-time updates.
    Implements query result caching to prevent duplicate executions.
    """
    
    def __init__(self, wrapped_server: MCPServer, stream_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None):
        """
        Args:
            wrapped_server: The actual MCP server to wrap
            stream_callback: Optional async callback function to stream messages when tools are called.
                           Should accept a dict with 'type', 'tool_name', 'query' (optional), and 'message' keys.
        """
        super().__init__(use_structured_content=wrapped_server.use_structured_content)
        self._wrapped = wrapped_server
        self._run_query_calls: List[Dict[str, Any]] = []
        self._stream_callback = stream_callback
        # Query result cache: maps query hash to cached result
        self._query_cache: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        return self._wrapped.name
    
    async def connect(self):
        await self._wrapped.connect()
    
    async def cleanup(self):
        await self._wrapped.cleanup()
    
    async def list_tools(self, run_context=None, agent=None):
        return await self._wrapped.list_tools(run_context, agent)
    
    def _get_query_hash(self, query: str) -> str:
        """Generate a hash for a query string to use as cache key."""
        return hashlib.sha256(query.encode('utf-8')).hexdigest()
    
    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None) -> Any:
        """
        Intercept tool calls and capture run_query calls along with their results.
        Streams temporary messages when tools are called.
        Implements caching for run_query calls to prevent duplicate executions.
        """
        # Handle run_query caching
        if tool_name == "run_query" and arguments:
            query = arguments.get("query", "")
            query_hash = self._get_query_hash(query)
            
            # Check cache first
            if query_hash in self._query_cache:
                cached_result = self._query_cache[query_hash]
                logger.info(
                    f"✅ CACHE HIT for run_query - returning cached result\n"
                    f"  - Query: {query[:150]}...\n"
                    f"  - Cache key: {query_hash[:16]}..."
                )
                
                # Extract structured content from cached result for tracking
                cached_content = extract_structured_content(cached_result)
                
                # Still track this call (but mark it as cached)
                call_index = len(self._run_query_calls)
                self._run_query_calls.append({
                    "query": query,
                    "index": call_index,
                    "result": cached_content,
                    "cached": True,  # Mark as cached
                })
                
                # Stream cached result message
                if self._stream_callback:
                    await self._stream_callback({
                        "type": "tool_call_start",
                        "tool_name": tool_name,
                        "query": query,
                        "message": f"Calling {tool_name} (cached):\n\n{query}",
                        "cached": True
                    })
                    await self._stream_callback({
                        "type": "tool_call_complete",
                        "tool_name": tool_name,
                        "message": f"Completed {tool_name} (from cache)",
                        "cached": True
                    })
                
                # Return cached result (original format preserved)
                return cached_result
            
            # Not in cache - proceed with execution
            logger.debug(f"Cache miss for query: {query[:100]}...")
        
        # Stream tool call start message
        if self._stream_callback:
            full_query = ""
            if tool_name == "run_query" and arguments:
                full_query = arguments.get("query", "")
            
            # Build full message with complete query
            if tool_name == "run_query" and full_query:
                message = f"Calling {tool_name}:\n\n{full_query}"
            else:
                message = f"Calling {tool_name}..."
            
            await self._stream_callback({
                "type": "tool_call_start",
                "tool_name": tool_name,
                "query": full_query if tool_name == "run_query" else None,
                "message": message
            })
        
        # Capture run_query calls (before execution)
        if tool_name == "run_query" and arguments:
            query = arguments.get("query", "")
            call_index = len(self._run_query_calls)
            self._run_query_calls.append({
                "query": query,
                "index": call_index,
                "result": None,  # Will be populated after the call
                "cached": False,  # Mark as not cached
            })
            logger.info(f"Intercepted run_query call #{call_index + 1}: {query[:100]}...")
        
        # Call the actual tool
        result = await self._wrapped.call_tool(tool_name, arguments)
        
        # Capture the result if this was a run_query call
        if tool_name == "run_query" and arguments:
            query = arguments.get("query", "")
            query_hash = self._get_query_hash(query)
            
            # Cache the original result object (preserves format)
            self._query_cache[query_hash] = result
            logger.debug(f"Cached result for query hash: {query_hash[:16]}...")
            
            # Extract structuredContent from result for tracking
            result_data = extract_structured_content(result)
            
            # Update the last call with the extracted result data
            if self._run_query_calls:
                self._run_query_calls[-1]["result"] = result_data
                logger.info(f"Captured result for run_query call #{len(self._run_query_calls)}")
        
        # Stream tool call completion message
        if self._stream_callback:
            await self._stream_callback({
                "type": "tool_call_complete",
                "tool_name": tool_name,
                "message": f"Completed {tool_name}"
            })
        
        return result
    
    async def list_prompts(self):
        return await self._wrapped.list_prompts()
    
    async def get_prompt(self, name: str, arguments: dict[str, Any] | None = None):
        return await self._wrapped.get_prompt(name, arguments)
    
    def get_run_query_calls(self) -> List[Dict[str, Any]]:
        """Get all intercepted run_query calls."""
        return self._run_query_calls.copy()
    
    def clear_run_query_calls(self):
        """Clear the intercepted run_query calls list."""
        self._run_query_calls.clear()
    
    def clear_cache(self):
        """Clear the query result cache."""
        self._query_cache.clear()
        logger.debug("Query cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        return {
            "cache_size": len(self._query_cache),
            "total_calls": len(self._run_query_calls),
            "cached_calls": sum(1 for call in self._run_query_calls if call.get("cached", False)),
        }
