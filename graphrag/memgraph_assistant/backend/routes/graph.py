"""
Graph visualization endpoints for Memgraph Assistant.
"""
import os
import logging
import sys
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from neo4j import GraphDatabase

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])

# Main graph connection settings (port 7688)
MEMGRAPH_URI = os.getenv("MEMGRAPH_MAIN_URI", "bolt://localhost:7688")
MEMGRAPH_USER = os.getenv("MEMGRAPH_USER", "")
MEMGRAPH_PASSWORD = os.getenv("MEMGRAPH_PASSWORD", "")

# Global driver instance
_driver = None


def get_driver():
    """Get Neo4j driver instance for main graph (reused across requests)."""
    global _driver
    if _driver is None:
        auth = None
        if MEMGRAPH_USER and MEMGRAPH_PASSWORD:
            auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD)
        _driver = GraphDatabase.driver(MEMGRAPH_URI, auth=auth)
    return _driver


class GraphQueryRequest(BaseModel):
    """Request model for graph queries."""
    query: Optional[str] = None


@router.post("/query")
async def query_graph(request: GraphQueryRequest):
    """
    Execute a Cypher query on the main graph and return results in a format suitable for visualization.
    
    Default query: MATCH (n) RETURN n
    """
    try:
        # Default query if none provided
        query = request.query or "MATCH (n) RETURN n"
        
        # Get driver and execute query
        driver = get_driver()
        
        with driver.session() as session:
            result = session.run(query)
            
            # Consume the result into a list first (Neo4j requires consuming before session closes)
            records = list(result)
            
            # Extract nodes and edges from result
            nodes = {}
            edges = []
            edge_id_counter = 0
            
            def process_node(node, nodes_dict):
                """Helper function to process a node and add it to nodes_dict."""
                node_id = str(node.id)
                if node_id not in nodes_dict:
                    labels = list(node.labels) if hasattr(node, 'labels') else []
                    
                    # Extract properties - Neo4j nodes use _properties attribute
                    properties = {}
                    if hasattr(node, '_properties'):
                        try:
                            props = node._properties
                            if props:
                                if isinstance(props, dict):
                                    properties = props
                                else:
                                    properties = dict(props)
                        except Exception as e:
                            logger.warning(f"Error extracting properties from node {node_id}: {e}")
                            properties = {}
                    elif hasattr(node, 'properties'):
                        # Fallback to properties if _properties doesn't exist
                        try:
                            props = node.properties
                            if props:
                                if isinstance(props, dict):
                                    properties = props
                                else:
                                    properties = dict(props)
                        except Exception as e:
                            logger.warning(f"Error extracting properties from node {node_id}: {e}")
                            properties = {}
                    
                    nodes_dict[node_id] = {
                        "id": node_id,
                        "label": properties.get('name') or properties.get('title') or (labels[0] if labels else node_id),
                        "labels": labels,
                        "properties": properties
                    }
                return node_id
            
            for record in records:
                # Process all values in the record
                for value in record.values():
                    if value is None:
                        continue
                    
                    # Check if it's a Node
                    if hasattr(value, 'id') and hasattr(value, 'labels'):
                        process_node(value, nodes)
                    
                    # Check if it's a Relationship
                    elif hasattr(value, 'start_node') and hasattr(value, 'end_node'):
                        rel = value
                        source_id = process_node(rel.start_node, nodes)
                        target_id = process_node(rel.end_node, nodes)
                        rel_type = rel.type if hasattr(rel, 'type') else 'RELATED_TO'
                        
                        # Extract relationship properties - Neo4j relationships use _properties
                        rel_props = {}
                        if hasattr(rel, '_properties'):
                            try:
                                props = rel._properties
                                if props:
                                    if isinstance(props, dict):
                                        rel_props = props
                                    else:
                                        rel_props = dict(props)
                            except Exception as e:
                                logger.warning(f"Error extracting properties from relationship: {e}")
                                rel_props = {}
                        elif hasattr(rel, 'properties'):
                            # Fallback to properties if _properties doesn't exist
                            try:
                                props = rel.properties
                                if props:
                                    if isinstance(props, dict):
                                        rel_props = props
                                    else:
                                        rel_props = dict(props)
                            except Exception as e:
                                logger.warning(f"Error extracting properties from relationship: {e}")
                                rel_props = {}
                        
                        edges.append({
                            "id": f"e{edge_id_counter}",
                            "source": source_id,
                            "target": target_id,
                            "label": rel_type,
                            "properties": rel_props
                        })
                        edge_id_counter += 1
        
        result = {
            "nodes": list(nodes.values()),
            "edges": edges,
            "query": query
        }

        return result
        
    except Exception as e:
        logger.error(f"Error executing graph query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error executing graph query: {str(e)}")
