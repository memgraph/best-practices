"""
MCP Server interceptor for capturing tool calls.
This module provides a wrapper around MCP servers to intercept and log tool calls,
particularly useful for capturing run_query calls.
"""
import logging
from typing import List, Dict, Any, Optional
from agents.mcp.server import MCPServer
from .common import extract_structured_content

logger = logging.getLogger(__name__)


def create_interceptor(
    base_server: MCPServer,
    name: Optional[str] = None
) -> "InterceptingMCPServer":
    """
    Create an InterceptingMCPServer wrapping the base MCP server.
    
    Args:
        base_server: The base MCPServer instance (must be used within async context)
        name: Optional name for the interceptor (for identification in logs/messages)
    
    Returns:
        InterceptingMCPServer instance
    """
    return InterceptingMCPServer(
        base_server,
        name=name
    )


class InterceptingMCPServer(MCPServer):
    """
    Wrapper around an MCP server that intercepts tool calls to capture run_query calls.
    This allows us to track all Cypher queries executed during a request.
    """
    
    def __init__(self, wrapped_server: MCPServer, name: Optional[str] = None):
        """
        Args:
            wrapped_server: The actual MCP server to wrap
            name: Optional name for the interceptor (for identification in logs/messages)
        """
        super().__init__(use_structured_content=wrapped_server.use_structured_content)
        self._wrapped = wrapped_server
        self._name = name or wrapped_server.name
        self._run_query_calls: List[Dict[str, Any]] = []
    
    @property
    def name(self) -> str:
        return self._name
    
    async def connect(self):
        await self._wrapped.connect()
    
    async def cleanup(self):
        await self._wrapped.cleanup()
    
    async def list_tools(self, run_context=None, agent=None):
        return await self._wrapped.list_tools(run_context, agent)
    
    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None) -> Any:
        """
        Intercept tool calls and capture run_query calls along with their results.
        """
        # Track run_query calls before execution
        if tool_name == "run_query" and arguments:
            query = arguments.get("query", "")
            call_index = len(self._run_query_calls)
            self._run_query_calls.append({
                "query": query,
                "index": call_index,
                "result": None,  # Will be populated after the call
            })
            logger.info(f"🔍 INTERCEPTOR {self._name}: Executing run_query call #{call_index + 1}\n  - Query: {query[:300]}...")
        
        # Call the actual tool
        result = await self._wrapped.call_tool(tool_name, arguments)
        
        # Capture the result if this was a run_query call
        if tool_name == "run_query" and arguments:
            query = arguments.get("query", "")
            result_data = extract_structured_content(result)
            
            # Update the last call with the extracted result data
            if self._run_query_calls:
                self._run_query_calls[-1]["result"] = result_data
                logger.info(f"✅ INTERCEPTOR: Captured result for run_query call #{len(self._run_query_calls)}")
        
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