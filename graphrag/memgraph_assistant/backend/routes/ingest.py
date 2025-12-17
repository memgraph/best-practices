"""
Ingestion endpoints for scraping and processing Memgraph documentation.
"""
import os
import json
import logging
import sys
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Request
import httpx
from bs4 import BeautifulSoup
import json
import asyncio
from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unstructured2graph import from_unstructured, compute_embeddings
from resources import initialize_resources
from routes.url_discovery import (
    discover_documentation_urls_stream,
    discover_documentation_urls,
    load_cached_urls_metadata,
    MEMGRAPH_DOCS_BASE_URL
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


def _escape_cypher_string(value: str) -> str:
    """Escape single quotes and backslashes for safe Cypher string interpolation."""
    return value.replace("\\", "\\\\").replace("'", "\\'")

# OpenAI client for extracting Cypher queries
OPENAI_CLIENT = None

def get_openai_client():
    """Get or create OpenAI client."""
    global OPENAI_CLIENT
    if OPENAI_CLIENT is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        OPENAI_CLIENT = OpenAI(api_key=api_key)
    return OPENAI_CLIENT


async def extract_cypher_queries_from_url(url: str) -> List[Dict[str, Any]]:
    """
    Extract Cypher queries from a documentation page using LLM.
    
    Args:
        url: The URL of the documentation page
        
    Returns:
        List of dictionaries with keys: entity_id, query, description
    """
    try:
        # Fetch the page content
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract text content (remove scripts, styles, etc.)
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Get main content
            main_content = soup.get_text(separator='\n', strip=True)
            
            # Limit content size to avoid token limits (keep first 15000 chars)
            if len(main_content) > 15000:
                main_content = main_content[:15000] + "..."
            
            # Extract page title/entity from URL or page
            entity_id = url.split('/')[-1] or url.split('/')[-2]
            # Try to get title from page
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text().strip()
                # Extract concept name from title (e.g., "PageRank - Memgraph Documentation" -> "pagerank")
                entity_id = title_text.split('-')[0].strip().lower().replace(' ', '')
            
            # Prepare prompt for LLM
            prompt = f"""Extract all Cypher queries from the following Memgraph documentation page.

URL: {url}
Entity/Concept: {entity_id}

Page Content:
{main_content}

Please extract all Cypher queries found in this documentation page and return them as a JSON object with a "queries" key containing an array. For each query, provide:
1. entity_id: The concept/feature being explained (e.g., "pagerank", "bfs", "shortest_path")
2. query: The raw Cypher query exactly as shown in the documentation
3. description: A brief description of what the query does

Return ONLY a valid JSON object in this format:
{{
  "queries": [
    {{
      "entity_id": "concept_name",
      "query": "CALL pagerank.get() YIELD node, rank;",
      "description": "Calculates the PageRank for the nodes in the graph."
    }},
    ...
  ]
}}

If no queries are found, return {{"queries": []}}.

Important:
- Extract queries exactly as written (preserve formatting, line breaks, etc.)
- Include all queries: examples, setup queries, result queries, etc.
- The entity_id should represent the main concept being explained on this page
- Return valid JSON only, no markdown formatting or explanations"""

            # Call OpenAI API
            client = get_openai_client()
            model = os.getenv("CHAT_MODEL", "gpt-4o")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts Cypher queries from documentation. Always return valid JSON with a 'queries' key containing an array."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Handle {"queries": [...]} format
            if isinstance(result, dict) and "queries" in result:
                queries = result["queries"]
            elif isinstance(result, list):
                # Fallback if LLM returns array directly
                queries = result
            else:
                logger.warning(f"Unexpected response format from LLM for {url}: {result}")
                queries = []
            
            # Validate and normalize queries
            normalized_queries = []
            for query_data in queries:
                if isinstance(query_data, dict) and "query" in query_data:
                    normalized_queries.append({
                        "entity_id": query_data.get("entity_id", entity_id),
                        "query": query_data.get("query", ""),
                        "description": query_data.get("description", "")
                    })
            
            logger.info(f"Extracted {len(normalized_queries)} Cypher queries from {url}")
            return normalized_queries
            
    except Exception as e:
        logger.error(f"Error extracting Cypher queries from {url}: {str(e)}", exc_info=True)
        return []


async def is_url_processed(memgraph, url: str) -> bool:
    """
    Check if a URL has already been processed.
    
    Args:
        memgraph: Memgraph database connection
        url: The URL to check
        
    Returns:
        True if URL has been processed, False otherwise
    """
    try:
        url_escaped = _escape_cypher_string(url)
        result = memgraph.query(f"MATCH (p:ProcessedUrls {{url: '{url_escaped}'}}) RETURN p LIMIT 1")
        return len(result) > 0
    except Exception as e:
        logger.warning(f"Error checking if URL is processed {url}: {str(e)}")
        return False


async def mark_url_as_processed(memgraph, url: str):
    """
    Mark a URL as processed by creating/merging a ProcessedUrls node.

    Args:
        memgraph: Memgraph database connection
        url: The URL that was processed
    """
    try:
        url_escaped = _escape_cypher_string(url)
        memgraph.query(f"MERGE (p:ProcessedUrls {{url: '{url_escaped}'}})")
        logger.debug(f"Marked URL as processed: {url}")
    except Exception as e:
        logger.warning(f"Error marking URL as processed {url}: {str(e)}")


async def insert_url_nodes(memgraph, urls_metadata: List[Dict[str, Any]]):
    """
    Insert discovered URLs with metadata into Memgraph as Url nodes.
    Creates a node for each URL with metadata properties (name, description, keywords).
    Creates HAS_CHILD_LINK relationships for children_urls and HAS_CONTENT_LINK for content_links.

    Args:
        memgraph: Memgraph database connection
        urls_metadata: List of URL metadata dictionaries with keys: url, description, keywords, children_urls, content_links
    """
    if not urls_metadata:
        return

    inserted_count = 0
    child_link_count = 0
    content_link_count = 0
    
    for url_data in urls_metadata:
        try:
            # Extract URL and metadata
            if isinstance(url_data, dict):
                url = url_data.get("url", "")
                description = url_data.get("description", "")
                keywords = url_data.get("keywords", "")
                children_urls = url_data.get("children_urls", [])
                content_links = url_data.get("content_links", [])
            else:
                url = url_data
                description = keywords = ""
                children_urls = []
                content_links = []

            if not url:
                continue

            # Skip URLs with no metadata and no links
            if not description and not keywords and not children_urls and not content_links:
                logger.debug(f"Skipping URL with no metadata and no links: {url}")
                continue

            # Create/update URL node
            url_escaped = _escape_cypher_string(url)
            description_escaped = _escape_cypher_string(description)
            keywords_escaped = _escape_cypher_string(keywords)
            
            memgraph.query(f"""
                MERGE (u:Url {{name: '{url_escaped}'}})
                SET u += {{description: '{description_escaped}', keywords: '{keywords_escaped}'}}
            """)
            inserted_count += 1

            # Create HAS_CHILD_LINK relationships for children_urls
            if children_urls:
                parent_escaped = url_escaped
                for child_url in children_urls:
                    try:
                        child_escaped = _escape_cypher_string(child_url)
                        memgraph.query(f"""
                            MERGE (parent:Url {{name: '{parent_escaped}'}})
                            MERGE (child:Url {{name: '{child_escaped}'}})
                            MERGE (parent)-[:HAS_CHILD_LINK]->(child)
                        """)
                        child_link_count += 1
                    except Exception as e:
                        logger.warning(f"Error creating HAS_CHILD_LINK relationship from {url} to {child_url}: {str(e)}")

            # Create HAS_CONTENT_LINK relationships for content_links
            if content_links:
                parent_escaped = url_escaped
                for content_url in content_links:
                    try:
                        content_escaped = _escape_cypher_string(content_url)
                        memgraph.query(f"""
                            MERGE (parent:Url {{name: '{parent_escaped}'}})
                            MERGE (content:Url {{name: '{content_escaped}'}})
                            MERGE (parent)-[:HAS_CONTENT_LINK]->(content)
                        """)
                        content_link_count += 1
                    except Exception as e:
                        logger.warning(f"Error creating HAS_CONTENT_LINK relationship from {url} to {content_url}: {str(e)}")
        except Exception as e:
            logger.warning(f"Error processing URL {url_data}: {str(e)}")

    logger.info(f"Inserted {inserted_count} Url nodes, {child_link_count} HAS_CHILD_LINK relationships, and {content_link_count} HAS_CONTENT_LINK relationships into Memgraph")


async def store_cypher_queries(memgraph, queries: List[Dict[str, Any]], source_url: str):
    """
    Store extracted Cypher queries in Memgraph.
    
    Args:
        memgraph: Memgraph database connection
        queries: List of query dictionaries with entity_id, query, description
        source_url: The URL where queries were extracted from
    """
    if not queries:
        return
    
    for query_data in queries:
        try:
            entity_id = query_data.get("entity_id", "").strip()
            query_text = query_data.get("query", "").strip()
            description = query_data.get("description", "").strip()
            
            if not entity_id or not query_text:
                logger.warning(f"Skipping query with missing entity_id or query: {query_data}")
                continue
            
            # Escape strings for safe Cypher interpolation
            entity_id_escaped = _escape_cypher_string(entity_id)
            query_text_escaped = _escape_cypher_string(query_text).replace("\n", "\\n")
            description_escaped = _escape_cypher_string(description)
            source_url_escaped = _escape_cypher_string(source_url)
            
            memgraph.query(f"""
                CREATE (q:CypherQuery {{
                    entity_id: '{entity_id_escaped}',
                    query: '{query_text_escaped}',
                    description: '{description_escaped}',
                    source_url: '{source_url_escaped}'
                }})
            """)
        except Exception as e:
            logger.warning(f"Error storing query for entity {query_data.get('entity_id')}: {str(e)}")


async def insert_url_nodes_from_metadata(
    memgraph,
    urls_metadata_discovered: List[Dict[str, Any]]
):
    """
    Insert URL nodes with metadata into Memgraph.
    Uses discovered metadata if available.

    Args:
        memgraph: Memgraph database connection
        urls_metadata_discovered: Metadata from discovery (if discovery was used) - contains URLs in metadata
    """
    if not urls_metadata_discovered:
        logger.warning("No discovered metadata available. Cannot create URL nodes without metadata.")
        return

    # Use discovered metadata - only insert valid URLs
    urls_metadata_to_insert = []
    valid_count = sum(1 for u in urls_metadata_discovered if isinstance(u, dict) and u.get("valid", True))
    logger.info(f"Using discovered metadata for {len(urls_metadata_discovered)} URLs ({valid_count} valid)")
    for url_meta in urls_metadata_discovered:
        # Only process valid URLs
        if isinstance(url_meta, dict) and not url_meta.get("valid", True):
            logger.debug(f"Skipping invalid URL: {url_meta.get('url', 'unknown')}")
            continue
        url = url_meta.get("url", url_meta) if isinstance(url_meta, dict) else url_meta
        if not await is_url_processed(memgraph, url):
            urls_metadata_to_insert.append(url_meta)

    if urls_metadata_to_insert:
        logger.info(f"Inserting {len(urls_metadata_to_insert)} URL nodes with metadata into Memgraph...")
        await insert_url_nodes(memgraph, urls_metadata_to_insert)


@router.post("/batch")
async def ingest_batch_documents(request: Request):
    """
    Ingest multiple documents from URLs into Memgraph.
    Processes documents one by one and returns success when all are done.

    Expected JSON body:
    {
        "urls": ["url1", "url2", ...],  # URLs to ingest (optional - if not provided, will discover all docs)
        "scrape_cypher_queries": true,
        "only_chunks": false,
        "link_chunks": true,
        "create_vector_index": true,
        "create_text_index": true,
        "cleanup": false
    }
    """
    # Parse request body
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    
    # Extract parameters with defaults
    urls = body.get("urls", [])
    scrape_cypher_queries = body.get("scrape_cypher_queries", True)
    only_chunks = body.get("only_chunks", False)
    link_chunks = body.get("link_chunks", True)
    create_vector_index = body.get("create_vector_index", True)
    create_text_index = body.get("create_text_index", True)
    cleanup = body.get("cleanup", False)

    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key."
        )

    urls_metadata_discovered = load_cached_urls_metadata()
    if not urls_metadata_discovered:
        urls_metadata_discovered = await discover_documentation_urls()

    # If no URLs provided, extract URLs from discovered metadata for processing (only valid ones)
    if not urls or not isinstance(urls, list) or len(urls) == 0:
        urls = [
            u.get("url", u) if isinstance(u, dict) else u 
            for u in urls_metadata_discovered 
            if isinstance(u, dict) and u.get("valid", True)
        ]
        logger.info(f"Extracted {len(urls)} valid URLs from discovered metadata for processing")

    try:
        logger.info(f"Processing batch of {len(urls)} documents. Starting ingestion...")

        # Initialize resources once at the beginning (with cleanup and vector index if requested)
        memgraph, lightrag_wrapper = await initialize_resources(
            cleanup=cleanup,
            create_vector_index=create_vector_index,
            create_text_index=create_text_index
        )

        # Insert URL nodes with metadata (always enabled)
        await insert_url_nodes_from_metadata(
            memgraph,
            urls_metadata_discovered
        )

        # Process documents one by one - from_unstructured called once per URL
        processed_count = 0
        skipped_count = 0

        for idx, url in enumerate(urls, 1):
            # Check if URL has already been processed
            if await is_url_processed(memgraph, url):
                logger.info(f"Skipping already processed document {idx}/{len(urls)}: {url}")
                skipped_count += 1
                continue

            logger.info(f"Processing document {idx}/{len(urls)}: {url}")

            # Extract Cypher queries from the page if enabled
            if scrape_cypher_queries:
                logger.info(f"Extracting Cypher queries from {url}...")
                cypher_queries = await extract_cypher_queries_from_url(url)

                # Store extracted Cypher queries in Memgraph
                if cypher_queries:
                    logger.info(f"Storing {len(cypher_queries)} Cypher queries in Memgraph...")
                    await store_cypher_queries(memgraph, cypher_queries, url)

            # Ingest single document
            await from_unstructured(
                [url],
                memgraph,
                lightrag_wrapper,
                only_chunks=only_chunks,
                link_chunks=link_chunks,
            )

            # Mark URL as processed
            await mark_url_as_processed(memgraph, url)
            processed_count += 1

        # Compute embeddings after all documents are ingested (index is already created by initialize_resources)
        if create_vector_index:
            logger.info("Computing embeddings for all chunks...")
            try:
                compute_embeddings(memgraph, "Chunk")
                logger.info("Successfully computed embeddings")
            except Exception as e:
                logger.warning(f"Error computing embeddings: {str(e)}")

        logger.info(f"Successfully ingested {processed_count} document(s) into Memgraph! ({skipped_count} skipped)")

        return {
            "message": f"Successfully ingested {processed_count} document(s) into Memgraph!",
            "urls_processed": processed_count,
            "urls_skipped": skipped_count,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error during batch ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during batch ingestion: {str(e)}"
        )

