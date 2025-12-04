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
            logger.info(
                f"🔍 vector_search_on_chunks called\n"
                f"  - Question: '{question[:100]}{'...' if len(question) > 100 else ''}'\n"
                f"  - Limit: {limit}"
            )
            
            # Use MCP server's call_tool method - this will go through the interceptor
            tool_result = await mcp_server.call_tool(
                "run_query", {"query": cypher_query}
            )

            # Extract structuredContent from MCP tool result
            content = extract_structured_content(tool_result)

            if content is None:
                logger.warning("vector_search_on_chunks: No structuredContent found in tool result")
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
            
            # Count results
            result_count = len(cleaned_content) if isinstance(cleaned_content, list) else 1
            logger.info(
                f"✅ vector_search_on_chunks completed successfully\n"
                f"  - Results found: {result_count}\n"
                f"  - Question: '{question[:50]}{'...' if len(question) > 50 else ''}'"
            )
            
            # Return as JSON string
            return json.dumps(cleaned_content, indent=2)

        except Exception as e:
            logger.error(
                f"❌ Error executing vector_search_on_chunks\n"
                f"  - Question: '{question[:100]}{'...' if len(question) > 100 else ''}'\n"
                f"  - Error: {str(e)}",
                exc_info=True
            )
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

        # Construct query to get properties and sample values for each property
        cypher_query = f"""MATCH (n:`{sanitized_label}`)
WITH collect(DISTINCT keys(n)) as all_keys, collect(n) as nodes
WITH all_keys, nodes[0..{sample_limit}] as sample_nodes
WITH all_keys[0] as properties_list, sample_nodes
UNWIND properties_list as property_key
RETURN property_key, [node IN sample_nodes | node[property_key]] as sampled_values_for_property"""

        try:
            logger.info(
                f"🔍 inspect_node_properties called\n"
                f"  - Label: '{label}'\n"
                f"  - Sample limit: {sample_limit}"
            )
            
            tool_result = await mcp_server.call_tool(
                "run_query", {"query": cypher_query}
            )

            # Extract structuredContent from MCP tool result
            content = extract_structured_content(tool_result)

            if content is None:
                logger.warning(f"inspect_node_properties: No structuredContent found for label '{label}'")
                return json.dumps(
                    {"error": "No structuredContent found in tool result"}
                )

            # Format the response nicely
            # The new query returns a list of rows, each with property_key and sampled_values_for_property
            result = {
                "label": label,
                "properties": []
            }

            # Process the results - each row contains a property_key and its sampled values
            if isinstance(content, list):
                for row in content:
                    if isinstance(row, dict):
                        property_key = row.get("property_key")
                        sampled_values = row.get("sampled_values_for_property", [])
                        if property_key:
                            result["properties"].append({
                                "key": property_key,
                                "sampled_values": sampled_values
                            })
            elif isinstance(content, dict):
                # Single result format (shouldn't happen with new query, but handle it)
                property_key = content.get("property_key")
                sampled_values = content.get("sampled_values_for_property", [])
                if property_key:
                    result["properties"].append({
                        "key": property_key,
                        "sampled_values": sampled_values
                    })

            property_count = len(result["properties"])
            logger.info(
                f"✅ inspect_node_properties completed successfully\n"
                f"  - Label: '{label}'\n"
                f"  - Properties found: {property_count}"
            )

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(
                f"❌ Error executing inspect_node_properties\n"
                f"  - Label: '{label}'\n"
                f"  - Sample limit: {sample_limit}\n"
                f"  - Error: {str(e)}",
                exc_info=True,
            )
            return json.dumps({"error": f"Error inspecting node properties: {str(e)}"})

    return inspect_node_properties


def create_keyword_search_tool(mcp_server: MCPServer):
    """
    Create a keyword_search tool that performs text search on a specific property.
    
    Args:
        mcp_server: MCP server instance to use for queries (should be InterceptingMCPServer)
        
    Returns:
        A function_tool decorated function for keyword search
    """
    @function_tool
    async def keyword_search(property_name: str, search_term: str, limit: int = 10) -> str:
        """
        Perform keyword search on nodes using text_search.search_all on a specific property.
        
        This tool searches for nodes where the specified property contains the search term.
        It uses Memgraph's text_search module to find matching nodes and returns them ordered by relevance score.
        
        Args:
            property_name: The property name to search on (e.g., "entity_id", "text", "name")
            search_term: The keyword or phrase to search for
            limit: Maximum number of results to return (default: 10)
            
        Returns:
            JSON string containing:
            - results: List of matching nodes with their relevance scores, ordered by score descending
            - Each result contains: node (with all properties) and score (relevance score)
        """
        # Sanitize inputs to prevent Cypher injection
        sanitized_property = property_name.replace("'", "").replace("\\", "").replace("`", "")
        sanitized_term = search_term.replace("'", "\\'").replace("\\", "\\\\")
        
        # Construct the keyword search query
        cypher_query = f"""CALL text_search.search_all("{sanitized_property}", "{sanitized_term}") YIELD node, score
RETURN node, score
ORDER BY score DESC
LIMIT {limit}"""
        
        try:
            logger.info(
                f"🔍 keyword_search called\n"
                f"  - Property: '{property_name}'\n"
                f"  - Search term: '{search_term[:100]}{'...' if len(search_term) > 100 else ''}'\n"
                f"  - Limit: {limit}"
            )
            
            tool_result = await mcp_server.call_tool("run_query", {"query": cypher_query})
            
            # Extract structuredContent from MCP tool result
            content = extract_structured_content(tool_result)
            
            if content is None:
                logger.warning(
                    f"keyword_search: No structuredContent found\n"
                    f"  - Property: '{property_name}'\n"
                    f"  - Search term: '{search_term[:50]}{'...' if len(search_term) > 50 else ''}'"
                )
                return json.dumps({"error": "No structuredContent found in tool result"})
            
            # Format the response
            result = {
                "property_searched": property_name,
                "search_term": search_term,
                "results": []
            }
            
            # Handle different response formats
            if isinstance(content, list):
                for row in content:
                    if isinstance(row, dict):
                        node_data = row.get("node", {})
                        score = row.get("score", 0.0)
                        result["results"].append({
                            "node": node_data,
                            "score": score
                        })
            elif isinstance(content, dict):
                # Single result format
                if "node" in content and "score" in content:
                    result["results"].append({
                        "node": content.get("node", {}),
                        "score": content.get("score", 0.0)
                    })
            
            result_count = len(result["results"])
            logger.info(
                f"✅ keyword_search completed successfully\n"
                f"  - Property: '{property_name}'\n"
                f"  - Search term: '{search_term[:50]}{'...' if len(search_term) > 50 else ''}'\n"
                f"  - Results found: {result_count}"
            )
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(
                f"❌ Error executing keyword_search\n"
                f"  - Property: '{property_name}'\n"
                f"  - Search term: '{search_term[:100]}{'...' if len(search_term) > 100 else ''}'\n"
                f"  - Limit: {limit}\n"
                f"  - Error: {str(e)}",
                exc_info=True
            )
            return json.dumps({"error": f"Error executing keyword search: {str(e)}"})
    
    return keyword_search


def create_relevance_expansion_tool(mcp_server: MCPServer):
    """
    Create a relevance_expansion tool that expands from a node ID to its neighborhood.
    
    Args:
        mcp_server: MCP server instance to use for queries (should be InterceptingMCPServer)
        
    Returns:
        A function_tool decorated function for relevance expansion
    """
    @function_tool
    async def relevance_expansion(node_id: int) -> str:
        """
        Expand from a node by ID to explore its neighborhood (connected nodes and relationships).
        
        This tool retrieves all nodes and relationships connected to a given node, allowing
        exploration of the graph structure around an interesting node. Useful for discovering
        related entities, context, or additional information connected to a node of interest.
        
        Args:
            node_id: The internal Memgraph node ID to expand from
            
        Returns:
            JSON string containing:
            - center_node: The central node that was expanded from (with all properties)
            - neighbors: List of neighboring nodes (with all properties)
            - relationships: List of relationships connecting the center node to neighbors
            - Each relationship entry contains: type, properties, and connected node info
        """
        # Validate node_id is an integer
        try:
            node_id_int = int(node_id)
        except (ValueError, TypeError):
            logger.error(
                f"❌ Invalid node_id for relevance_expansion\n"
                f"  - Provided node_id: {node_id}\n"
                f"  - Error: Must be an integer"
            )
            return json.dumps({"error": f"Invalid node_id: {node_id}. Must be an integer."})
        
        logger.info(
            f"🔍 relevance_expansion called\n"
            f"  - Node ID: {node_id_int}"
        )
        
        # Construct the relevance expansion query
        cypher_query = f"""MATCH (n)-[r]-(m) 
WHERE id(n) = {node_id_int} 
RETURN n as center_node, 
       collect(DISTINCT {{relationship: r, neighbor: m}}) as connections"""
        
        try:
            tool_result = await mcp_server.call_tool("run_query", {"query": cypher_query})
            
            # Extract structuredContent from MCP tool result
            content = extract_structured_content(tool_result)
            
            if content is None:
                logger.warning(
                    f"relevance_expansion: No structuredContent found\n"
                    f"  - Node ID: {node_id_int}"
                )
                return json.dumps({"error": "No structuredContent found in tool result"})
            
            # Format the response
            result = {
                "center_node": None,
                "neighbors": [],
                "relationships": []
            }
            
            # Handle different response formats
            if isinstance(content, list) and len(content) > 0:
                row = content[0]
                if isinstance(row, dict):
                    # Center node
                    center_node = row.get("center_node", {})
                    if center_node:
                        result["center_node"] = center_node
                    
                    # Connections
                    connections = row.get("connections", [])
                    neighbors_set = set()  # Use set to avoid duplicates
                    relationships_list = []
                    
                    for conn in connections:
                        if isinstance(conn, dict):
                            rel_data = conn.get("relationship", {})
                            neighbor = conn.get("neighbor", {})
                            
                            if neighbor:
                                # Add neighbor (using node ID as key to avoid duplicates)
                                neighbor_id = neighbor.get("id") if isinstance(neighbor, dict) else None
                                if neighbor_id not in neighbors_set:
                                    neighbors_set.add(neighbor_id)
                                    result["neighbors"].append(neighbor)
                            
                            if rel_data:
                                # Extract relationship info
                                rel_info = {
                                    "type": rel_data.get("type", ""),
                                    "properties": rel_data.get("properties", {}),
                                    "start_node_id": rel_data.get("start_node_id"),
                                    "end_node_id": rel_data.get("end_node_id")
                                }
                                relationships_list.append(rel_info)
                    
                    result["relationships"] = relationships_list
            elif isinstance(content, dict):
                # Single result format
                center_node = content.get("center_node", {})
                if center_node:
                    result["center_node"] = center_node
                
                connections = content.get("connections", [])
                neighbors_set = set()
                relationships_list = []
                
                for conn in connections:
                    if isinstance(conn, dict):
                        rel_data = conn.get("relationship", {})
                        neighbor = conn.get("neighbor", {})
                        
                        if neighbor:
                            neighbor_id = neighbor.get("id") if isinstance(neighbor, dict) else None
                            if neighbor_id not in neighbors_set:
                                neighbors_set.add(neighbor_id)
                                result["neighbors"].append(neighbor)
                        
                        if rel_data:
                            rel_info = {
                                "type": rel_data.get("type", ""),
                                "properties": rel_data.get("properties", {}),
                                "start_node_id": rel_data.get("start_node_id"),
                                "end_node_id": rel_data.get("end_node_id")
                            }
                            relationships_list.append(rel_info)
                
                result["relationships"] = relationships_list
            
            neighbor_count = len(result["neighbors"])
            relationship_count = len(result["relationships"])
            logger.info(
                f"✅ relevance_expansion completed successfully\n"
                f"  - Node ID: {node_id_int}\n"
                f"  - Neighbors found: {neighbor_count}\n"
                f"  - Relationships found: {relationship_count}"
            )
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(
                f"❌ Error executing relevance_expansion\n"
                f"  - Node ID: {node_id_int}\n"
                f"  - Error: {str(e)}",
                exc_info=True
            )
            return json.dumps({"error": f"Error executing relevance expansion: {str(e)}"})
    
    return relevance_expansion
