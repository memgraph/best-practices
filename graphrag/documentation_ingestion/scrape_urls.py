"""
URL discovery functionality for scraping and discovering Memgraph documentation URLs.
Stores URLs as JSON objects with metadata: valid, keywords, summary, content_links.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
from collections import deque

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

from prompts import (
    KEYWORDS_SYSTEM_PROMPT,
    KEYWORDS_USER_PROMPT_TEMPLATE,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_PROMPT_TEMPLATE,
)
from scrape_cypher import extract_cypher_queries_from_content
from database import store_cypher_queries, update_url_metadata
from models import DocumentationUrl

logger = logging.getLogger(__name__)

MEMGRAPH_DOCS_BASE_URL = "https://memgraph.com/docs"
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "discovered_urls.json")
_openai_client: Optional[OpenAI] = None


def get_openai_client() -> Optional[OpenAI]:
    global _openai_client
    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            _openai_client = OpenAI(api_key=api_key)
        else:
            logger.warning("OPENAI_API_KEY not set. LLM features (keywords, summary) will be skipped.")
    return _openai_client


async def _llm_call(system_prompt: str, user_prompt: str) -> str:
    """Helper for LLM calls."""
    client = get_openai_client()
    if not client:
        return ""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"LLM error: {str(e)}")
        return ""


async def extract_keywords_with_llm(content: str, url: str) -> List[str]:
    truncated = content[:4000]
    result = await _llm_call(KEYWORDS_SYSTEM_PROMPT, KEYWORDS_USER_PROMPT_TEMPLATE.format(content=truncated))
    if not result:
        return []
    try:
        parsed = json.loads(result.strip())
        return [str(k).strip() for k in parsed if k] if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


async def summarize_with_llm(content: str, url: str) -> str:
    return await _llm_call(SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT_TEMPLATE.format(content=content[:4000]))


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_cached_urls() -> List[Dict[str, Any]]:
    ensure_cache_dir()
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            if data and isinstance(data[0], str):
                logger.info(f"Converting {len(data)} URLs from old format")
                return [{"url": u, "valid": None, "keywords": [], "summary": "", "content_links": [], "depth": -1} for u in data]
            
            logger.info(f"Loaded {len(data)} URLs from cache")
            return data
        return data.get('urls', []) if isinstance(data, dict) else []
    except Exception as e:
        logger.warning(f"Error loading cache: {str(e)}")
        return []


def save_urls_to_cache(urls: List[Dict[str, Any]]):
    ensure_cache_dir()
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(urls, f, indent=2)
        logger.info(f"Saved {len(urls)} URLs to cache")
    except Exception as e:
        logger.warning(f"Error saving cache: {str(e)}")


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    return normalized if len(normalized) == 1 or not normalized.endswith('/') else normalized[:-1]


def is_valid_docs_url(url: str) -> bool:
    if not url.startswith(MEMGRAPH_DOCS_BASE_URL):
        return False
    return not any(p in url for p in ['/api/', '/search', '/404', '.pdf', '.zip', '.tar.gz', '#'])


def get_cleaned_inner_main(soup: BeautifulSoup, require_nested: bool = False) -> Any:
    outer_main = soup.find('main')
    if not outer_main:
        if require_nested:
            raise ValueError("No outer <main> tag found")
        inner_main = soup.find('body') or soup
    else:
        inner_main = outer_main.find('main') or (outer_main if not require_nested else None)
        if not inner_main and require_nested:
            raise ValueError("No nested <main> tag found inside outer <main> tag")
        inner_main = inner_main or outer_main
    
    for tag in ["script", "style", "nav", "aside", "header", "footer"]:
        for element in inner_main(tag):
            element.decompose()
    return inner_main


def extract_text_content(soup: BeautifulSoup) -> str:
    return get_cleaned_inner_main(soup, require_nested=False).get_text(separator=' ', strip=True)


async def extract_links_from_element(element: Any, base_url: str, exclude_base: bool = True) -> List[str]:
    """Extract valid doc URLs from an element."""
    found = set()
    base_norm = normalize_url(base_url)
    for link in element.find_all('a', href=True):
        href = link.get('href', '')
        if href:
            normalized = normalize_url(urljoin(base_url, href))
            if exclude_base and (normalized == base_norm or base_norm.startswith(normalized + '/')):
                continue
            if is_valid_docs_url(normalized):
                found.add(normalized)
    return sorted(list(found))


async def extract_content_links(soup: BeautifulSoup, base_url: str, inner_main: Optional[Any] = None) -> List[str]:
    if inner_main is None:
        try:
            inner_main = get_cleaned_inner_main(soup, require_nested=True)
        except ValueError as e:
            raise ValueError(f"{str(e)} for URL: {base_url}") from e
    return await extract_links_from_element(inner_main, base_url, exclude_base=True)


async def process_url_content(memgraph, urls: List[str]) -> int:
    """
    Process URL content to extract and ingest Cypher queries, description, and keywords.
    
    Returns:
        Total number of Cypher queries extracted and stored
    """
    logger.info(f"Processing content from {len(urls)} URLs")
    cypher_queries_count = 0
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for idx, url in enumerate(urls, 1):
            try:
                logger.info(f"[{idx}/{len(urls)}] Processing: {url}")
                response = await client.get(url)
                response.raise_for_status()
                
                if 'text/html' not in response.headers.get('content-type', '').lower():
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                text_content = extract_text_content(soup)
                
                if text_content:
                    queries = await extract_cypher_queries_from_content(text_content, url, soup)
                    if queries:
                        await store_cypher_queries(memgraph, queries, url)
                        cypher_queries_count += len(queries)
                    
                    keywords = await extract_keywords_with_llm(text_content, url)
                    summary = await summarize_with_llm(text_content, url)
                    update_url_metadata(memgraph, url, summary, keywords, len(text_content))
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                continue
    
    logger.info(f"Processed {len(urls)} URLs")
    return cypher_queries_count


async def discover_urls(base_url: str = MEMGRAPH_DOCS_BASE_URL) -> List[DocumentationUrl]:
    """
    Discover URLs by crawling from the base URL and following content links.
    
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
                url_to_content_links[normalized] = content_links
                
                for link_url in content_links:
                    normalized_link = normalize_url(link_url)
                    if normalized_link not in discovered:
                        discovered.add(normalized_link)
                        queue.append(link_url)
            except (httpx.HTTPStatusError, httpx.TimeoutException, Exception) as e:
                logger.warning(f"Error scraping {current_url}: {str(e)}")
                continue
    
    result = [
        DocumentationUrl(url=url, content_urls=url_to_content_links.get(url, []))
        for url in sorted(discovered)
    ]
    
    logger.info(f"Discovered {len(result)} URLs from {base_url}")
    return result
