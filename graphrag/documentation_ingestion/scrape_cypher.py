"""
Cypher query extraction from documentation pages with caching support.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from scrape_urls import extract_text_content
from common import llm_call_json
from prompts import (
    CYPHER_QUERIES_SYSTEM_PROMPT,
    CYPHER_QUERIES_USER_PROMPT_TEMPLATE
)
from models import CypherQuery

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "cypher_queries.json")


def ensure_cache_dir():
    """Ensure cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_cached_queries() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load cached Cypher queries from disk.
    
    Returns:
        Dictionary mapping URLs to lists of query dictionaries with keys: entity_id, query, description
    """
    ensure_cache_dir()
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
        if isinstance(data, dict):
            logger.info(f"Loaded cached Cypher queries for {len(data)} URLs")
            return data
        logger.warning(f"Unexpected cache format, expected dict, got {type(data)}")
        return {}
    except Exception as e:
        logger.warning(f"Error loading Cypher queries cache: {str(e)}")
        return {}


def save_queries_to_cache(queries_cache: Dict[str, List[Dict[str, Any]]]):
    """
    Save Cypher queries cache to disk.
    Only saves URLs that have at least one query (filters out empty lists).
    
    Args:
        queries_cache: Dictionary mapping URLs to lists of query dictionaries
    """
    ensure_cache_dir()
    try:
        # Filter out empty query lists
        filtered_cache = {url: queries for url, queries in queries_cache.items() if queries}
        with open(CACHE_FILE, 'w') as f:
            json.dump(filtered_cache, f, indent=2)
        logger.info(f"Saved Cypher queries cache for {len(filtered_cache)} URLs (filtered {len(queries_cache) - len(filtered_cache)} empty entries)")
    except Exception as e:
        logger.warning(f"Error saving Cypher queries cache: {str(e)}")


async def extract_cypher_queries_from_url(url: str, use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Extract Cypher queries from a documentation page using LLM.
    Uses cache if available and use_cache is True.
    
    Args:
        url: The URL of the documentation page
        use_cache: If True, check cache first and save results to cache
        
    Returns:
        List of dictionaries with keys: entity_id, query, description
    """
    # Check cache first
    if use_cache:
        cached_queries = load_cached_queries()
        if url in cached_queries:
            logger.info(f"Using cached Cypher queries for {url} ({len(cached_queries[url])} queries)")
            return cached_queries[url]
    
    try:
        # Fetch the page content
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Parse HTML and extract text content using scrape_urls utility
            soup = BeautifulSoup(response.text, 'html.parser')
            main_content = extract_text_content(soup)
            
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
            
            # Prepare prompt using prompts.py template
            user_prompt = CYPHER_QUERIES_USER_PROMPT_TEMPLATE.format(
                url=url,
                entity_id=entity_id,
                content=main_content
            )
            
            # Call LLM using common.py utility
            model = os.getenv("CHAT_MODEL", "gpt-4o")
            result = await llm_call_json(
                system_prompt=CYPHER_QUERIES_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=model,
                temperature=0.1
            )
            
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
            
            # Save to cache only if there are queries
            if use_cache and normalized_queries:
                cached_queries = load_cached_queries()
                cached_queries[url] = normalized_queries
                save_queries_to_cache(cached_queries)
            
            return normalized_queries
            
    except Exception as e:
        logger.error(f"Error extracting Cypher queries from {url}: {str(e)}", exc_info=True)
        return []


async def extract_cypher_queries_from_urls(
    urls: List[str],
    use_cache: bool = True
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract Cypher queries from multiple URLs.
    
    Args:
        urls: List of URLs to extract queries from
        use_cache: If True, check cache first and save results to cache
        
    Returns:
        Dictionary mapping URLs to lists of query dictionaries
    """
    results = {}
    
    for idx, url in enumerate(urls, 1):
        logger.info(f"[{idx}/{len(urls)}] Extracting Cypher queries from: {url}")
        queries = await extract_cypher_queries_from_url(url, use_cache=use_cache)
        if queries:
            results[url] = queries
    
    return results


def _smart_chunk_content(text: str, max_chunk_size: int = 12000) -> List[str]:
    """
    Split content into chunks at natural boundaries.
    Tries to split at section headers, double newlines, or single newlines.
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    remaining = text
    
    while remaining:
        if len(remaining) <= max_chunk_size:
            chunks.append(remaining)
            break
        
        # Try to find a good split point within the limit
        chunk = remaining[:max_chunk_size]
        
        # Priority: section headers (##), then double newlines, then single newlines
        split_idx = -1
        for delimiter in ['\n## ', '\n\n', '\n']:
            idx = chunk.rfind(delimiter)
            if idx > max_chunk_size // 2:  # Only split if we keep at least half
                split_idx = idx + (len(delimiter) if delimiter == '\n## ' else 0)
                break
        
        if split_idx == -1:
            split_idx = max_chunk_size  # Hard split as fallback
        
        chunks.append(remaining[:split_idx].strip())
        remaining = remaining[split_idx:].strip()
    
    return [c for c in chunks if c]


async def _extract_from_chunk(chunk: str, url: str, entity_id: str) -> List[CypherQuery]:
    """Extract Cypher queries from a single chunk."""
    user_prompt = CYPHER_QUERIES_USER_PROMPT_TEMPLATE.format(
        url=url,
        entity_id=entity_id,
        content=chunk
    )
    
    model = os.getenv("CHAT_MODEL", "gpt-4o")
    result = await llm_call_json(
        system_prompt=CYPHER_QUERIES_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=model,
        temperature=0.1
    )
    
    if isinstance(result, dict) and "queries" in result:
        queries = result["queries"]
    elif isinstance(result, list):
        queries = result
    else:
        return []
    
    normalized = []
    for q in queries:
        if isinstance(q, dict) and "query" in q:
            normalized.append(CypherQuery(
                entity_id=q.get("entity_id", entity_id),
                query=q.get("query", ""),
                description=q.get("description", "")
            ))
    return normalized


async def extract_cypher_queries_from_content(
    text_content: str,
    url: str,
    soup: BeautifulSoup
) -> List[CypherQuery]:
    """
    Extract Cypher queries from text content using LLM with smart chunking.
    """
    try:
        # Extract entity_id from page title
        entity_id = url.split('/')[-1] or url.split('/')[-2]
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text().strip()
            entity_id = title_text.split('-')[0].strip().lower().replace(' ', '_')
        
        # Smart chunk the content
        chunks = _smart_chunk_content(text_content)
        logger.info(f"Cypher extraction: {len(text_content)} chars -> {len(chunks)} chunk(s) for {url}")
        
        # Process all chunks
        all_queries = []
        seen_queries = set()  # Dedupe by query text
        
        for chunk in chunks:
            chunk_queries = await _extract_from_chunk(chunk, url, entity_id)
            for q in chunk_queries:
                if q.query not in seen_queries:
                    seen_queries.add(q.query)
                    all_queries.append(q)
        
        logger.info(f"Extracted {len(all_queries)} unique Cypher queries from {url}")
        return all_queries
        
    except Exception as e:
        logger.error(f"Error extracting Cypher queries from {url}: {str(e)}", exc_info=True)
        return []

