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
import logging
import asyncio
from pathlib import Path
from typing import List


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

from unstructured2graph import compute_embeddings
from scrape_sidebar import discover_sidebar_elements
from scrape_urls import (
    MEMGRAPH_DOCS_BASE_URL,
    process_url_content,
    discover_urls,
)

from database import ingest_sidebar_elements, ingest_documentation_urls
from process_kg import initialize_memgraph_and_lightrag, knowledge_graph_construction


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

