"""
Cypher query extraction from documentation pages.
"""
import os
import logging
from typing import List

from bs4 import BeautifulSoup

from common import llm_call_json
from prompts import (
    CYPHER_QUERIES_SYSTEM_PROMPT,
    CYPHER_QUERIES_USER_PROMPT_TEMPLATE
)
from models import CypherQuery

logger = logging.getLogger(__name__)


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

