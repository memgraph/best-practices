#!/usr/bin/env python3
"""
Standalone script to scrape Memgraph documentation and create a knowledge graph using LightRAG.

This script:
1. Discovers all documentation pages from memgraph.com/docs
2. Processes each page using unstructured2graph
3. Creates a knowledge graph in Memgraph using LightRAG
4. Computes embeddings for semantic search
"""

import os
import sys
import json
import logging
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import deque
import httpx
from bs4 import BeautifulSoup


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Path setup for imports
SCRIPT_DIR = Path(__file__).parent.absolute()

# Add ai-toolkit paths to sys.path (similar to memgraph_assistant)
AI_TOOLKIT_DIR = SCRIPT_DIR / "ai-toolkit"
UNSTRUCTURED2GRAPH_PATH = AI_TOOLKIT_DIR / "unstructured2graph" / "src"
LIGHTRAG_PATH = AI_TOOLKIT_DIR / "integrations" / "lightrag-memgraph" / "src"
MEMGRAPH_TOOLBOX_PATH = AI_TOOLKIT_DIR / "memgraph-toolbox" / "src"

sys.path.insert(0, str(UNSTRUCTURED2GRAPH_PATH))
sys.path.insert(0, str(LIGHTRAG_PATH))
sys.path.insert(0, str(MEMGRAPH_TOOLBOX_PATH))

# Import after path setup
from lightrag_memgraph import MemgraphLightRAGWrapper
from unstructured2graph import from_unstructured, compute_embeddings, create_index, create_vector_search_index
from memgraph_toolbox.api.memgraph import Memgraph

# Import sidebar processing
from scrape_sidebar import discover_sidebar_elements

# Import URL discovery
from scrape_urls import (
    extract_content_links,
    normalize_url,
    is_valid_docs_url,
    MEMGRAPH_DOCS_BASE_URL,
    extract_text_content,
    extract_keywords_with_llm,
    summarize_with_llm
)

# Import Cypher query extraction
from scrape_cypher import extract_cypher_queries_from_content

# Import database operations
from database import (
    ingest_sidebar_elements,
    ingest_documentation_urls,
    store_cypher_queries,
    update_url_metadata,
    check_url_processed,
    mark_url_processed,
)

# Import models
from models import DocumentationUrl


async def discover_urls(base_url: str = MEMGRAPH_DOCS_BASE_URL) -> List[DocumentationUrl]:
    """
    Discover URLs by crawling from the base URL and following content links.
    
    Args:
        base_url: Base URL to start discovery from (default: MEMGRAPH_DOCS_BASE_URL)
        
    Returns:
        List of DocumentationUrl objects with url and content_urls
    """
    logger.info(f"Discovering URLs from {base_url}")
    
    discovered: Set[str] = set()
    url_to_content_links: Dict[str, List[str]] = {}
    queue = deque([base_url])
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        while queue:
            current_url = queue.popleft()
            normalized = normalize_url(current_url)
            
            if normalized in discovered:
                continue
            
            discovered.add(normalized)
            
            try:
                response = await client.get(current_url)
                response.raise_for_status()
                if 'text/html' not in response.headers.get('content-type', '').lower():
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                content_links = await extract_content_links(soup, current_url)
                
                # Store content links for this URL
                url_to_content_links[normalized] = content_links
                
                for link_url in content_links:
                    normalized_link = normalize_url(link_url)
                    if normalized_link not in discovered:
                        discovered.add(normalized_link)
                        queue.append(link_url)
            except (httpx.HTTPStatusError, httpx.TimeoutException, Exception) as e:
                logger.warning(f"Error scraping {current_url}: {str(e)}")
                continue
    
    # Convert to DocumentationUrl objects
    result = [
        DocumentationUrl(url=url, content_urls=url_to_content_links.get(url, []))
        for url in sorted(discovered)
    ]
    
    logger.info(f"Discovered {len(result)} URLs from {base_url}")
    return result


async def process_url_content(
    memgraph: Memgraph,
    urls: List[str]
) -> int:
    """
    Process URL content to extract and ingest information:
    - Cypher queries
    - Description and keywords
    
    Args:
        memgraph: Memgraph database connection
        urls: List of URLs to process
        
    Returns:
        Total number of Cypher queries extracted and stored
    """
    logger.info(f"Processing content from {len(urls)} URLs")
    
    cypher_queries_count = 0
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for idx, url in enumerate(urls, 1):
            try:
                logger.info(f"[{idx}/{len(urls)}] Processing: {url}")
                
                # Fetch the page
                response = await client.get(url)
                response.raise_for_status()
                
                if 'text/html' not in response.headers.get('content-type', '').lower():
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                text_content = extract_text_content(soup)
                
                # Extract description, keywords, and Cypher queries
                if text_content:
                    # Extract Cypher queries from text content
                    queries = await extract_cypher_queries_from_content(text_content, url, soup)
                    if queries:
                        await store_cypher_queries(memgraph, queries, url)
                        cypher_queries_count += len(queries)
                    
                    # Extract description and keywords
                    keywords = await extract_keywords_with_llm(text_content, url)
                    summary = await summarize_with_llm(text_content, url)
                    
                    # Update URL node with description and keywords
                    update_url_metadata(memgraph, url, summary, keywords)
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                continue
    
    logger.info(f"Processed {len(urls)} URLs")
    return cypher_queries_count


async def knowledge_graph_construction(
    memgraph: Memgraph,
    lightrag_wrapper: MemgraphLightRAGWrapper,
    urls: List[str],
    skip_processed: bool = False
) -> tuple[int, int, int]:
    """
    Construct knowledge graph by processing URLs with LightRAG and unstructured2graph.
    
    Args:
        memgraph: Memgraph instance
        lightrag_wrapper: LightRAG wrapper instance
        urls: List of URLs to process
        skip_processed: If True, skip URLs that have already been processed
        
    Returns:
        Tuple of (processed_count, skipped_count, error_count)
    """
    logger.info(f"Constructing knowledge graph from {len(urls)} URLs")
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for idx, url in enumerate(urls, 1):
        try:
            # Skip if already processed
            if skip_processed and check_url_processed(memgraph, url):
                logger.info(f"[{idx}/{len(urls)}] Skipping already processed: {url}")
                skipped_count += 1
                continue
            
            logger.info(f"[{idx}/{len(urls)}] Processing: {url}")
            
            await process_document(
                memgraph,
                lightrag_wrapper,
                url
            )
            
            # Mark URL as processed after successful processing
            mark_url_processed(memgraph, url)
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            error_count += 1
            continue
    
    return processed_count, skipped_count, error_count


async def initialize_memgraph_and_lightrag(
    cleanup: bool = False
) -> tuple[Memgraph, MemgraphLightRAGWrapper]:
    """
    Initialize Memgraph connection and LightRAG wrapper.
    Always creates vector index and text indexes.
    
    Args:
        cleanup: If True, drop all existing data
    
    Returns:
        Tuple of (Memgraph instance, LightRAG wrapper)
    """
    logger.info("Initializing Memgraph and LightRAG...")
    
    # Create Memgraph instance
    memgraph = Memgraph()
    
    # Cleanup if requested
    if cleanup:
        logger.info("Cleaning up existing data...")
        try:
            memgraph.query("STORAGE MODE IN_MEMORY_ANALYTICAL")
            memgraph.query("DROP GRAPH")
            memgraph.query("STORAGE MODE IN_MEMORY_TRANSACTIONAL")
            logger.info("Successfully cleaned up existing data")
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
    
    # Create indexes (always created)
    try:
        create_index(memgraph, "Chunk", "hash")
        logger.info("Created index on Chunk(hash)")
    except Exception as e:
        logger.warning(f"Index may already exist: {str(e)}")
    
    # Always create vector search index
    try:
        create_vector_search_index(memgraph, "Chunk", "embedding")
        logger.info("Created vector search index on Chunk(embedding)")
    except Exception as e:
        logger.warning(f"Vector index may already exist: {str(e)}")
    
    # Always create text indexes
    text_indexes = [
        ("entity_id", "base", "entity_id"),
        ("text", "Chunk", "text"),
        ("query", "CypherQuery", "query"),
        ("url_description", "Url", "description, keywords"),
    ]
    
    for index_name, label, properties in text_indexes:
        try:
            memgraph.query(f"CREATE TEXT INDEX {index_name} ON :{label}({properties});")
            logger.info(f"Created text index {index_name} on {label}({properties})")
        except Exception as e:
            logger.warning(f"Text index {index_name} may already exist: {str(e)}")
    
    # Setup LightRAG directory
    lightrag_dir = SCRIPT_DIR / "lightrag_storage.out"
    
    if cleanup and lightrag_dir.exists():
        try:
            shutil.rmtree(lightrag_dir)
            logger.info("Removed existing LightRAG directory")
        except Exception as e:
            logger.warning(f"Error removing LightRAG directory: {str(e)}")
    
    lightrag_dir.mkdir(exist_ok=True)
    
    # Create LightRAG wrapper
    lightrag_wrapper = MemgraphLightRAGWrapper(
        log_level="WARNING",
        disable_embeddings=True  # We'll compute embeddings separately
    )
    await lightrag_wrapper.initialize(working_dir=str(lightrag_dir))
    
    logger.info("Successfully initialized Memgraph and LightRAG")
    return memgraph, lightrag_wrapper


async def process_document(
    memgraph: Memgraph,
    lightrag_wrapper: MemgraphLightRAGWrapper,
    url: str
):
    """
    Process a single document URL.
    Always creates entities/relationships and links chunks together.
    
    Args:
        memgraph: Memgraph instance
        lightrag_wrapper: LightRAG wrapper instance
        url: URL to process
    """
    logger.info(f"Processing document: {url}")
    
    await from_unstructured(
        [url],
        memgraph,
        lightrag_wrapper,
        only_chunks=False,
        link_chunks=True,
    )
    logger.info(f"Successfully processed: {url}")


async def main():
    """Main function to orchestrate the scraping and ingestion process."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scrape Memgraph documentation and create a knowledge graph"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up existing data before ingestion"
    )
    parser.add_argument(
        "--skip-processed",
        action="store_true",
        help="Skip URLs that have already been processed"
    )
    parser.add_argument(
        "--max-urls",
        type=int,
        help="Maximum number of URLs to process (for testing)"
    )
    
    args = parser.parse_args()
    
    # Verify OPENAI_API_KEY is set (required for Cypher query extraction)
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key.")
    
    try:
        # Step 1: Initialize resources
        logger.info("=" * 80)
        logger.info("Step 1: Initializing Memgraph and LightRAG")
        logger.info("=" * 80)
        memgraph, lightrag_wrapper = await initialize_memgraph_and_lightrag(
            cleanup=args.cleanup
        )
        
        # Step 2: Discover sidebar elements
        logger.info("=" * 80)
        logger.info("Step 2: Discovering sidebar elements")
        logger.info("=" * 80)
        sidebar_urls = await discover_sidebar_elements()
        sidebar_urls_list = await ingest_sidebar_elements(memgraph, sidebar_urls)
        
        # Step 3: Discover and ingest URLs from base URL
        logger.info("=" * 80)
        logger.info("Step 3: Discovering and ingesting URLs from base URL")
        logger.info("=" * 80)
        discovered_urls = await discover_urls(MEMGRAPH_DOCS_BASE_URL)
        discovered_urls_list = await ingest_documentation_urls(memgraph, discovered_urls)
        
        # Combine sidebar URLs and discovered URLs
        all_urls_set = set(sidebar_urls_list) | set(discovered_urls_list)
        all_urls = sorted(list(all_urls_set))
        
        if args.max_urls:
            all_urls = all_urls[:args.max_urls]
            logger.info(f"Limited to {len(all_urls)} URLs for processing")
        
        if not all_urls:
            logger.error("No URLs discovered. Exiting.")
            return
        
        # Step 4: Process URL content (Cypher queries, description, keywords)
        logger.info("=" * 80)
        logger.info("Step 4: Processing URL content")
        logger.info("=" * 80)
        cypher_queries_count = await process_url_content(memgraph, all_urls)
        logger.info(f"Extracted and stored {cypher_queries_count} Cypher queries total")
        
        # Step 5: Knowledge graph construction
        logger.info("=" * 80)
        logger.info("Step 5: Knowledge graph construction")
        logger.info("=" * 80)
        processed_count, skipped_count, error_count = await knowledge_graph_construction(
            memgraph,
            lightrag_wrapper,
            all_urls,
            skip_processed=args.skip_processed
        )
        
        # Step 6: Compute embeddings (always done)
        logger.info("=" * 80)
        logger.info("Step 6: Computing embeddings")
        logger.info("=" * 80)
        try:
            compute_embeddings(memgraph, "Chunk")
            logger.info("Successfully computed embeddings for all chunks")
        except Exception as e:
            logger.error(f"Error computing embeddings: {str(e)}", exc_info=True)
        
        # Summary
        logger.info("=" * 80)
        logger.info("Ingestion Complete!")
        logger.info("=" * 80)
        logger.info(f"Total URLs: {len(all_urls)}")
        logger.info(f"Processed: {processed_count}")
        logger.info(f"Skipped: {skipped_count}")
        logger.info(f"Errors: {error_count}")
        
        # Cleanup LightRAG wrapper
        await lightrag_wrapper.afinalize()
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Exiting...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

