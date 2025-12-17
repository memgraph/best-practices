"""
Database operations for Memgraph insertion and querying.
"""
import json
import logging
import os
from pathlib import Path
from typing import List, Set, Dict, Any, Optional

from memgraph_toolbox.api.memgraph import Memgraph
from models import SidebarUrl, DocumentationUrl, CypherQuery

CACHE_FILE = Path(__file__).parent / "cache.json"

logger = logging.getLogger(__name__)


def escape_cypher_string(value: str) -> str:
    """Escape single quotes and backslashes for safe Cypher string interpolation."""
    return value.replace("\\", "\\\\").replace("'", "\\'")

# Keep backward compatibility
_escape_cypher_string = escape_cypher_string


async def ingest_sidebar_elements(memgraph: Memgraph, sidebar_urls: List[SidebarUrl]) -> List[str]:
    """
    Ingest sidebar URLs into Memgraph, creating nodes and relationships.
    
    Args:
        memgraph: Memgraph database connection
        sidebar_urls: List of SidebarUrl objects to ingest
        
    Returns:
        List of all unique URLs from sidebar (for later processing)
    """
    logger.info(f"Ingesting {len(sidebar_urls)} sidebar URLs into Memgraph")
    
    all_urls_set: Set[str] = set()
    inserted_count = 0
    child_relationship_count = 0
    
    for sidebar_url in sidebar_urls:
        try:
            url = sidebar_url.url
            children_urls = sidebar_url.children_urls
            
            if not url:
                continue
            
            # Add URL to set of all URLs
            all_urls_set.add(url)
            all_urls_set.update(children_urls)
            
            # Create/update URL node
            url_escaped = _escape_cypher_string(url)
            memgraph.query(f"""
                MERGE (u:Url {{name: '{url_escaped}'}})
            """)
            inserted_count += 1
            
            # Create HAS_CHILD_LINK relationships for children URLs
            if children_urls:
                for child_url in children_urls:
                    try:
                        child_escaped = _escape_cypher_string(child_url)
                        # Create nodes and relationship in one MERGE
                        memgraph.query(f"""
                            MERGE (parent:Url {{name: '{url_escaped}'}})
                            MERGE (child:Url {{name: '{child_escaped}'}})
                            MERGE (parent)-[:HAS_CHILD_LINK]->(child)
                        """)
                        child_relationship_count += 1
                    except Exception as e:
                        logger.warning(f"Error creating HAS_CHILD_LINK relationship from {url} to {child_url}: {str(e)}")
        except Exception as e:
            logger.warning(f"Error processing sidebar URL {sidebar_url.url}: {str(e)}")
    
    all_urls = sorted(list(all_urls_set))
    logger.info(f"Ingested {inserted_count} sidebar URL nodes and {child_relationship_count} HAS_CHILD_LINK relationships into Memgraph")
    logger.info(f"Collected {len(all_urls)} unique URLs from sidebar")
    return all_urls


async def store_cypher_queries(memgraph: Memgraph, queries: List[CypherQuery], source_url: str):
    """
    Store extracted Cypher queries in Memgraph and link to source URL.
    
    Args:
        memgraph: Memgraph database connection
        queries: List of CypherQuery objects
        source_url: The URL where queries were extracted from
    """
    if not queries:
        return
    
    source_url_escaped = _escape_cypher_string(source_url)
    
    for query in queries:
        try:
            entity_id = query.entity_id.strip()
            query_text = query.query.strip()
            description = query.description.strip()
            
            if not entity_id or not query_text:
                logger.warning(f"Skipping query with missing entity_id or query: {query}")
                continue
            
            entity_id_escaped = _escape_cypher_string(entity_id)
            query_text_escaped = _escape_cypher_string(query_text).replace("\n", "\\n")
            description_escaped = _escape_cypher_string(description)
            
            memgraph.query(f"""
                MERGE (u:Url {{name: '{source_url_escaped}'}})
                CREATE (q:CypherQuery {{
                    entity_id: '{entity_id_escaped}',
                    query: '{query_text_escaped}',
                    description: '{description_escaped}'
                }})
                CREATE (u)-[:HAS_CYPHER_QUERY]->(q)
            """)
        except Exception as e:
            logger.warning(f"Error storing query for entity {query.entity_id}: {str(e)}")


def update_url_metadata(memgraph: Memgraph, url: str, description: str, keywords: List[str], content_length: int = 0):
    """
    Update URL node with description, keywords, and content length.
    
    Args:
        memgraph: Memgraph database connection
        url: The URL to update
        description: Description/summary text
        keywords: List of keywords
        content_length: Length of the text content in characters
    """
    try:
        url_escaped = escape_cypher_string(url)
        keywords_str = ", ".join(keywords) if keywords else ""
        description_escaped = escape_cypher_string(description)
        keywords_escaped = escape_cypher_string(keywords_str)
        
        memgraph.query(f"""
            MATCH (u:Url {{name: '{url_escaped}'}})
            SET u += {{description: '{description_escaped}', keywords: '{keywords_escaped}', content_length: {content_length}}}
        """)
    except Exception as e:
        logger.warning(f"Error updating URL metadata for {url}: {str(e)}")


async def ingest_documentation_urls(memgraph: Memgraph, documentation_urls: List[DocumentationUrl]) -> List[str]:
    """
    Ingest DocumentationUrl objects into Memgraph, creating nodes and relationships.
    
    Args:
        memgraph: Memgraph database connection
        documentation_urls: List of DocumentationUrl objects to ingest
        
    Returns:
        List of all unique URLs from documentation URLs (for later processing)
    """
    logger.info(f"Ingesting {len(documentation_urls)} documentation URLs into Memgraph")
    
    all_urls_set: Set[str] = set()
    inserted_count = 0
    content_link_count = 0
    
    for doc_url in documentation_urls:
        try:
            url = doc_url.url
            content_urls = doc_url.content_urls
            
            if not url:
                continue
            
            # Add URL to set of all URLs
            all_urls_set.add(url)
            all_urls_set.update(content_urls)
            
            # Create/update URL node
            url_escaped = _escape_cypher_string(url)
            memgraph.query(f"""
                MERGE (u:Url {{name: '{url_escaped}'}})
            """)
            inserted_count += 1
            
            # Create HAS_CONTENT_LINK relationships for content URLs
            if content_urls:
                for content_url in content_urls:
                    try:
                        content_escaped = _escape_cypher_string(content_url)
                        # Create nodes and relationship in one MERGE
                        memgraph.query(f"""
                            MERGE (parent:Url {{name: '{url_escaped}'}})
                            MERGE (content:Url {{name: '{content_escaped}'}})
                            MERGE (parent)-[:HAS_CONTENT_LINK]->(content)
                        """)
                        content_link_count += 1
                    except Exception as e:
                        logger.warning(f"Error creating HAS_CONTENT_LINK relationship from {url} to {content_url}: {str(e)}")
        except Exception as e:
            logger.warning(f"Error processing documentation URL {doc_url.url}: {str(e)}")
    
    all_urls = sorted(list(all_urls_set))
    logger.info(f"Ingested {inserted_count} documentation URL nodes and {content_link_count} HAS_CONTENT_LINK relationships into Memgraph")
    logger.info(f"Collected {len(all_urls)} unique URLs from documentation URLs")
    return all_urls


def check_url_processed(memgraph: Memgraph, url: str) -> bool:
    """Check if a URL has already been processed."""
    try:
        url_escaped = escape_cypher_string(url)
        result = memgraph.query(f"MATCH (p:ProcessedUrls {{url: '{url_escaped}'}}) RETURN p LIMIT 1")
        return len(result) > 0
    except Exception as e:
        logger.warning(f"Error checking if URL is processed {url}: {str(e)}")
        return False


def mark_url_processed(memgraph: Memgraph, url: str):
    """Mark a URL as processed."""
    try:
        url_escaped = escape_cypher_string(url)
        memgraph.query(f"MERGE (p:ProcessedUrls {{url: '{url_escaped}'}})")
        logger.debug(f"Marked URL as processed: {url}")
    except Exception as e:
        logger.warning(f"Error marking URL as processed {url}: {str(e)}")


def cache_exists() -> bool:
    """Check if cache file exists."""
    return CACHE_FILE.exists()


def export_graph_to_cache(memgraph: Memgraph) -> Dict[str, Any]:
    """
    Export URL graph data from Memgraph to cache file.
    
    Returns:
        Dictionary with all URL data including content_links, children_urls, and cypher_queries
    """
    logger.info("Exporting graph data to cache")
    
    # Get all URLs with their properties
    urls_result = memgraph.query("""
        MATCH (u:Url)
        RETURN u.name AS url, u.description AS description, 
               u.keywords AS keywords, u.content_length AS content_length
    """)
    
    cache_data: Dict[str, Any] = {"urls": {}}
    
    for row in urls_result:
        url = row["url"]
        cache_data["urls"][url] = {
            "description": row.get("description", ""),
            "keywords": row.get("keywords", ""),
            "content_length": row.get("content_length", 0),
            "content_links": [],
            "children_urls": [],
            "cypher_queries": []
        }
    
    # Get content links (HAS_CONTENT_LINK relationships)
    content_links_result = memgraph.query("""
        MATCH (parent:Url)-[:HAS_CONTENT_LINK]->(content:Url)
        RETURN parent.name AS parent_url, content.name AS content_url
    """)
    for row in content_links_result:
        parent_url = row["parent_url"]
        if parent_url in cache_data["urls"]:
            cache_data["urls"][parent_url]["content_links"].append(row["content_url"])
    
    # Get children URLs (HAS_CHILD_LINK relationships)
    children_result = memgraph.query("""
        MATCH (parent:Url)-[:HAS_CHILD_LINK]->(child:Url)
        RETURN parent.name AS parent_url, child.name AS child_url
    """)
    for row in children_result:
        parent_url = row["parent_url"]
        if parent_url in cache_data["urls"]:
            cache_data["urls"][parent_url]["children_urls"].append(row["child_url"])
    
    # Get Cypher queries
    queries_result = memgraph.query("""
        MATCH (u:Url)-[:HAS_CYPHER_QUERY]->(q:CypherQuery)
        RETURN u.name AS url, q.entity_id AS entity_id, 
               q.query AS query, q.description AS description
    """)
    for row in queries_result:
        url = row["url"]
        if url in cache_data["urls"]:
            cache_data["urls"][url]["cypher_queries"].append({
                "entity_id": row["entity_id"],
                "query": row["query"],
                "description": row["description"]
            })
    
    # Save to cache file
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    logger.info(f"Exported {len(cache_data['urls'])} URLs to cache: {CACHE_FILE}")
    return cache_data


def load_cache() -> Optional[Dict[str, Any]]:
    """Load cache data from file."""
    if not cache_exists():
        return None
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading cache: {str(e)}")
        return None


def import_cache_to_graph(memgraph: Memgraph, cache_data: Dict[str, Any]) -> List[str]:
    """
    Import cached data into Memgraph.
    
    Args:
        memgraph: Memgraph database connection
        cache_data: Dictionary with cached URL data
        
    Returns:
        List of all URLs imported
    """
    logger.info("Importing cache data to Memgraph")
    
    urls_data = cache_data.get("urls", {})
    all_urls = []
    
    for url, data in urls_data.items():
        try:
            url_escaped = escape_cypher_string(url)
            description = escape_cypher_string(data.get("description", "") or "")
            keywords = escape_cypher_string(data.get("keywords", "") or "")
            content_length = data.get("content_length", 0) or 0
            
            # Create URL node with properties
            memgraph.query(f"""
                MERGE (u:Url {{name: '{url_escaped}'}})
                SET u.description = '{description}',
                    u.keywords = '{keywords}',
                    u.content_length = {content_length}
            """)
            all_urls.append(url)
            
            # Create content link relationships
            for content_url in data.get("content_links", []):
                content_escaped = escape_cypher_string(content_url)
                memgraph.query(f"""
                    MERGE (parent:Url {{name: '{url_escaped}'}})
                    MERGE (content:Url {{name: '{content_escaped}'}})
                    MERGE (parent)-[:HAS_CONTENT_LINK]->(content)
                """)
            
            # Create children relationships
            for child_url in data.get("children_urls", []):
                child_escaped = escape_cypher_string(child_url)
                memgraph.query(f"""
                    MERGE (parent:Url {{name: '{url_escaped}'}})
                    MERGE (child:Url {{name: '{child_escaped}'}})
                    MERGE (parent)-[:HAS_CHILD_LINK]->(child)
                """)
            
            # Create Cypher query nodes
            for query_data in data.get("cypher_queries", []):
                entity_id = escape_cypher_string(query_data.get("entity_id", ""))
                query_text = escape_cypher_string(query_data.get("query", "")).replace("\n", "\\n")
                query_desc = escape_cypher_string(query_data.get("description", ""))
                
                if entity_id and query_text:
                    memgraph.query(f"""
                        MERGE (u:Url {{name: '{url_escaped}'}})
                        CREATE (q:CypherQuery {{
                            entity_id: '{entity_id}',
                            query: '{query_text}',
                            description: '{query_desc}'
                        }})
                        CREATE (u)-[:HAS_CYPHER_QUERY]->(q)
                    """)
        except Exception as e:
            logger.warning(f"Error importing URL {url}: {str(e)}")
    
    logger.info(f"Imported {len(all_urls)} URLs from cache")
    return sorted(all_urls)

