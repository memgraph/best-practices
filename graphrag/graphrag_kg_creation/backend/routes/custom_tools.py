"""
Custom function tools for OpenAI Agents SDK.
These tools extend the capabilities of agents beyond MCP tools.
"""
import json
import logging
from agents.tool import function_tool
from agents.mcp.server import MCPServer
from .common import extract_structured_content

logger = logging.getLogger(__name__)


def create_vector_search_tool(mcp_server: MCPServer):
    """
    Create a vector_search_on_chunks tool that uses an MCP server (with interceptor).
    All queries will go through the interceptor.
    
    Args:
        mcp_server: MCP server instance to use for queries (should be InterceptingMCPServer)
        
    Returns:
        A function_tool decorated function for vector search
    """
    @function_tool
    async def vector_search_on_chunks(question: str, limit: int = 10) -> str:
        """
        Perform vector search on chunks in Memgraph using embeddings.

        This tool generates embeddings from the user's question and searches for similar chunks
        in the vector index 'vs_name'. It executes the query directly and returns results.

        Args:
            question: The user's question to search for
            limit: Maximum number of results to return (default: 10) - Recommendation is to use 10.

        Returns:
            JSON string containing the search results with nodes and similarity scores.
            Each result contains a node and its similarity score.
        """
        # Sanitize the question to prevent Cypher injection
        sanitized_query = question.replace("'", "\\'").replace("\\", "\\\\")

        # Construct the vector search query exactly as specified
        cypher_query = f"""CALL embeddings.text(["{sanitized_query}"]) yield dimension, embeddings, success
WITH embeddings[0] as embedding
CALL vector_search.search("vs_name", {limit}, embedding) YIELD distance, node, similarity
RETURN node, similarity"""

        try:
            # Use MCP server's call_tool method - this will go through the interceptor
            tool_result = await mcp_server.call_tool("run_query", {"query": cypher_query})
            
            # Extract structuredContent from MCP tool result
            content = extract_structured_content(tool_result)
            
            if content is None:
                return json.dumps({"error": "No structuredContent found in tool result"})
            
            # Remove "embedding" fields to save tokens
            def remove_embeddings(obj):
                """Recursively remove 'embedding' keys from the object."""
                if isinstance(obj, dict):
                    return {
                        k: remove_embeddings(v) 
                        for k, v in obj.items() 
                        if k != "embedding"
                    }
                elif isinstance(obj, list):
                    return [remove_embeddings(item) for item in obj]
                else:
                    return obj
            
            cleaned_content = remove_embeddings(content)
            # Return as JSON string
            return json.dumps(cleaned_content, indent=2)

        except Exception as e:
            logger.error(f"Error executing vector search: {str(e)}", exc_info=True)
            return json.dumps({"error": f"Error executing vector search: {str(e)}"})
    
    return vector_search_on_chunks



