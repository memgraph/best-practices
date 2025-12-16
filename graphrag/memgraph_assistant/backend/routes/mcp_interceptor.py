"""
MCP Server interceptor for capturing tool calls.
This module provides a wrapper around MCP servers to intercept and log tool calls,
particularly useful for capturing run_query calls.
"""
import logging
from typing import List, Dict, Any, Optional, Callable, Awaitable
from agents.mcp.server import MCPServer
from .common import extract_structured_content

logger = logging.getLogger(__name__)


def create_interceptor(
    base_server: MCPServer,
    name: Optional[str] = None,
    message_callback: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[None]]] = None
) -> "InterceptingMCPServer":
    """
    Create an InterceptingMCPServer wrapping the base MCP server.
    
    Args:
        base_server: The base MCPServer instance (must be used within async context)
        name: Optional name for the interceptor (for identification in logs/messages)
        message_callback: Optional async callback function(tool_name, interceptor_name, data) to send messages to frontend
    
    Returns:
        InterceptingMCPServer instance
    """
    return InterceptingMCPServer(
        base_server,
        name=name,
        message_callback=message_callback
    )


class InterceptingMCPServer(MCPServer):
    """
    Wrapper around an MCP server that intercepts tool calls to capture run_query calls.
    This allows us to track all Cypher queries executed during a request.
    """
    
    def __init__(
        self, 
        wrapped_server: MCPServer, 
        name: Optional[str] = None,
        message_callback: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[None]]] = None
    ):
        """
        Args:
            wrapped_server: The actual MCP server to wrap
            name: Optional name for the interceptor (for identification in logs/messages)
            message_callback: Optional async callback function(tool_name, interceptor_name, data) to send messages to frontend
        """
        super().__init__(use_structured_content=wrapped_server.use_structured_content)
        self._wrapped = wrapped_server
        self._name = name or wrapped_server.name
        self._run_query_calls: List[Dict[str, Any]] = []
        self._message_callback = message_callback
    
    @property
    def name(self) -> str:
        return self._name
    
    async def connect(self):
        await self._wrapped.connect()
    
    async def cleanup(self):
        await self._wrapped.cleanup()
    
    async def list_tools(self, run_context=None, agent=None):
        return await self._wrapped.list_tools(run_context, agent)
    
    async def _send_tool_call_message(
        self, 
        tool_name: str, 
        arguments: dict[str, Any] | None
    ) -> None:
        """
        Send a message to the frontend via the message callback when a tool is called.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Arguments passed to the tool
        """
        if not self._message_callback:
            return
        
        try:
            await self._message_callback(
                tool_name,
                self._name,
                {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "status": "calling"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send tool call message: {e}")
    
    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None) -> Any:
        """
        Intercept tool calls and capture run_query calls along with their results.
        """
        is_run_query = tool_name == "run_query" and arguments
        is_log_message = tool_name == "log_message"
        
        # Send message to frontend when tool is called
        await self._send_tool_call_message(tool_name, arguments)
        
        # Handle log_message specially - it's not a real MCP tool, just for logging
        if is_log_message:
            # Return the message as the result without calling wrapped server
            # The message was already sent to frontend via _send_tool_call_message
            message = arguments.get("message", "") if arguments else ""
            return {"message": message}
        
        # Track run_query calls before execution
        if is_run_query:
            query = arguments.get("query", "")
            call_index = len(self._run_query_calls)
            self._run_query_calls.append({
                "query": query,
                "index": call_index,
                "result": None,  # Will be populated after the call
            })
            logger.info(f"🔍 MCP {self._name}: Executing run_query call #{call_index + 1}\n  - Query: {query[:300]}...")
        
        # Call the actual tool
        result = await self._wrapped.call_tool(tool_name, arguments)
        
        # Capture the result if this was a run_query call
        if is_run_query:
            query = arguments.get("query", "")
            result_data = extract_structured_content(result)
            
            # Update the last call with the extracted result data
            if self._run_query_calls:
                self._run_query_calls[-1]["result"] = result_data
                logger.info(f"✅ MCP: Captured result for run_query call #{len(self._run_query_calls)}")
        
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