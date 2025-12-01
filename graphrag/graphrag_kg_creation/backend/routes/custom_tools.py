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
            tool_result = await mcp_server.call_tool(
                "run_query", {"query": cypher_query}
            )

            # Extract structuredContent from MCP tool result
            content = extract_structured_content(tool_result)

            if content is None:
                return json.dumps(
                    {"error": "No structuredContent found in tool result"}
                )

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


def create_inspect_node_properties_tool(mcp_server: MCPServer):
    """
    Create an inspect_node_properties tool that inspects properties of nodes with a specific label.

    Args:
        mcp_server: MCP server instance to use for queries (should be InterceptingMCPServer)

    Returns:
        A function_tool decorated function for inspecting node properties
    """

    @function_tool
    async def inspect_node_properties(label: str, sample_limit: int = 5) -> str:
        """
        Inspect properties of nodes with a specific label in Memgraph.

        This tool queries the graph to discover what properties exist on nodes with the given label,
        and also returns the sample property values to understand the data structure.

        Args:
            label: The node label to inspect (e.g., "Chunk", "Person", "Document")
            sample_limit: Maximum number of sample nodes to return (default: 5)

        Returns:
            JSON string containing:
            - properties: List of property keys found on nodes with this label
            - sample_nodes: Sample nodes with their property values (limited by sample limit)
        """
        # Sanitize the label to prevent Cypher injection
        # Labels in Cypher are typically alphanumeric with underscores, but we'll be safe
        sanitized_label = label.replace("'", "").replace("\\", "").replace("`", "")

        # Construct query to get properties and sample nodes
        # Use a simple approach that works without apoc
        cypher_query = f"""MATCH (n:`{sanitized_label}`)
WITH collect(DISTINCT keys(n)) as all_keys, collect(n) as nodes
WITH all_keys, nodes[0..{sample_limit}] as sample_nodes
WITH all_keys[0] as properties_list, sample_nodes
RETURN properties_list as properties,
       [node IN sample_nodes | properties(node)] as sample_property_values"""

        try:
            tool_result = await mcp_server.call_tool(
                "run_query", {"query": cypher_query}
            )

            # Extract structuredContent from MCP tool result
            content = extract_structured_content(tool_result)

            if content is None:
                return json.dumps(
                    {"error": "No structuredContent found in tool result"}
                )

            # Format the response nicely
            result = {
                "label": label,
                "properties": (
                    content.get("properties", []) if isinstance(content, dict) else []
                ),
                "sample_property_values": (
                    content.get("sample_property_values", [])
                    if isinstance(content, dict)
                    else []
                ),
                "node_count": (
                    content.get("node_count", 0) if isinstance(content, dict) else 0
                ),
            }

            # If content is a list, try to extract from first element
            if isinstance(content, list) and len(content) > 0:
                first_result = content[0]
                if isinstance(first_result, dict):
                    result["properties"] = first_result.get("properties", [])
                    result["sample_property_values"] = first_result.get(
                        "sample_property_values", []
                    )
                    result["node_count"] = first_result.get("node_count", 0)

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(
                f"Error inspecting node properties for label {label}: {str(e)}",
                exc_info=True,
            )
            return json.dumps({"error": f"Error inspecting node properties: {str(e)}"})

    return inspect_node_properties


def create_get_adjacent_chunks_tool(mcp_server: MCPServer):
    """
    Create a get_adjacent_chunks tool that retrieves previous and next chunks from a reference chunk.
    
    Args:
        mcp_server: MCP server instance to use for queries (should be InterceptingMCPServer)
        
    Returns:
        A function_tool decorated function for getting adjacent chunks
    """
    @function_tool
    async def get_adjacent_chunks(chunk_hash: str) -> str:
        """
        Retrieve previous and next chunks from a reference chunk using the NEXT relationship.
        Retrieves chunks at depth 2 (immediate neighbors and their neighbors).
        
        This tool finds chunks that are adjacent to the given chunk in the document sequence.
        It uses OPTIONAL MATCH to handle cases where a chunk might not have a previous or next chunk.
        Returns up to 2 levels deep: immediate previous/next chunks and their adjacent chunks.
        
        Args:
            chunk_hash: The hash property value of the reference chunk to find adjacent chunks for
            
        Returns:
            JSON string containing:
            - reference_chunk: The reference chunk with id and text
            - previous_chunks: List of previous chunks (up to 2 levels deep) with id and text, ordered from closest to farthest
            - next_chunks: List of next chunks (up to 2 levels deep) with id and text, ordered from closest to farthest
        """
        # Sanitize the chunk_hash to prevent Cypher injection
        sanitized_hash = chunk_hash.replace("'", "\\'").replace("\\", "\\\\")
        
        # Construct query using OPTIONAL MATCH to find previous and next chunks at depth 2
        # We'll traverse up to 2 hops in each direction
        cypher_query = f"""MATCH (ref:Chunk {{hash: '{sanitized_hash}'}})
OPTIONAL MATCH (prev1:Chunk)-[:NEXT]->(ref)
OPTIONAL MATCH (prev2:Chunk)-[:NEXT]->(prev1)
OPTIONAL MATCH (ref)-[:NEXT]->(next1:Chunk)
OPTIONAL MATCH (next1)-[:NEXT]->(next2:Chunk)
WITH ref,
     [chunk IN collect(DISTINCT prev1) WHERE chunk IS NOT NULL | {{id: id(chunk), text: chunk.text, depth: 1}}] as prev_level1,
     [chunk IN collect(DISTINCT prev2) WHERE chunk IS NOT NULL | {{id: id(chunk), text: chunk.text, depth: 2}}] as prev_level2,
     [chunk IN collect(DISTINCT next1) WHERE chunk IS NOT NULL | {{id: id(chunk), text: chunk.text, depth: 1}}] as next_level1,
     [chunk IN collect(DISTINCT next2) WHERE chunk IS NOT NULL | {{id: id(chunk), text: chunk.text, depth: 2}}] as next_level2
RETURN id(ref) as reference_id,
       ref.text as reference_text,
       prev_level1 + prev_level2 as previous_chunks,
       next_level1 + next_level2 as next_chunks"""
        
        try:
            tool_result = await mcp_server.call_tool("run_query", {"query": cypher_query})
            
            # Extract structuredContent from MCP tool result
            content = extract_structured_content(tool_result)
            
            if content is None:
                return json.dumps({"error": "No structuredContent found in tool result"})
            
            # Format the response
            result = {
                "reference_chunk": None,
                "previous_chunks": [],
                "next_chunks": []
            }
            
            # Handle different response formats
            if isinstance(content, list) and len(content) > 0:
                row = content[0]
                if isinstance(row, dict):
                    # Reference chunk
                    if row.get("reference_id") is not None:
                        result["reference_chunk"] = {
                            "id": row.get("reference_id"),
                            "text": row.get("reference_text")
                        }
                    
                    # Previous chunks (up to depth 2)
                    prev_chunks = row.get("previous_chunks", [])
                    if prev_chunks:
                        # Filter out None values and sort by depth
                        prev_chunks_clean = [
                            {"id": ch.get("id"), "text": ch.get("text"), "depth": ch.get("depth")}
                            for ch in prev_chunks
                            if ch and ch.get("id") is not None
                        ]
                        result["previous_chunks"] = sorted(prev_chunks_clean, key=lambda x: x.get("depth", 0))
                    
                    # Next chunks (up to depth 2)
                    next_chunks = row.get("next_chunks", [])
                    if next_chunks:
                        # Filter out None values and sort by depth
                        next_chunks_clean = [
                            {"id": ch.get("id"), "text": ch.get("text"), "depth": ch.get("depth")}
                            for ch in next_chunks
                            if ch and ch.get("id") is not None
                        ]
                        result["next_chunks"] = sorted(next_chunks_clean, key=lambda x: x.get("depth", 0))
            elif isinstance(content, dict):
                # Single result format
                if content.get("reference_id") is not None:
                    result["reference_chunk"] = {
                        "id": content.get("reference_id"),
                        "text": content.get("reference_text")
                    }
                
                # Previous chunks
                prev_chunks = content.get("previous_chunks", [])
                if prev_chunks:
                    prev_chunks_clean = [
                        {"id": ch.get("id"), "text": ch.get("text"), "depth": ch.get("depth")}
                        for ch in prev_chunks
                        if ch and ch.get("id") is not None
                    ]
                    result["previous_chunks"] = sorted(prev_chunks_clean, key=lambda x: x.get("depth", 0))
                
                # Next chunks
                next_chunks = content.get("next_chunks", [])
                if next_chunks:
                    next_chunks_clean = [
                        {"id": ch.get("id"), "text": ch.get("text"), "depth": ch.get("depth")}
                        for ch in next_chunks
                        if ch and ch.get("id") is not None
                    ]
                    result["next_chunks"] = sorted(next_chunks_clean, key=lambda x: x.get("depth", 0))
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting adjacent chunks for hash {chunk_hash}: {str(e)}", exc_info=True)
            return json.dumps({"error": f"Error getting adjacent chunks: {str(e)}"})
    
    return get_adjacent_chunks
