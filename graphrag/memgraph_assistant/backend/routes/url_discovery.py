"""
URL discovery functionality for scraping and discovering Memgraph documentation URLs.
"""
import os
import json
import logging
from typing import List, Dict, Any
from collections import deque
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

logger = logging.getLogger(__name__)

# Base URL for Memgraph documentation
MEMGRAPH_DOCS_BASE_URL = "https://memgraph.com/docs"

# Cache file for discovered URLs with metadata
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "discovered_urls_metadata.json")

# OpenAI client for extracting metadata
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


def ensure_cache_dir():
    """Ensure the cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_cached_urls_metadata() -> List[Dict[str, Any]]:
    """Load cached URLs with metadata from file if it exists."""
    ensure_cache_dir()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Support both old and new format
                if isinstance(data, dict) and 'urls' in data:
                    # New format with metadata
                    urls_metadata = data.get('urls', [])
                    # Ensure all entries have children_urls, content_links, and valid fields
                    for url_meta in urls_metadata:
                        if isinstance(url_meta, dict):
                            if 'children_urls' not in url_meta:
                                url_meta['children_urls'] = []
                            if 'content_links' not in url_meta:
                                url_meta['content_links'] = []
                            if 'valid' not in url_meta:
                                url_meta['valid'] = True  # Default to True for backward compatibility
                    logger.info(f"Loaded {len(urls_metadata)} URLs with metadata from cache")
                    return urls_metadata
                elif isinstance(data, dict) and 'url' in data:
                    # Old format - convert to list
                    old_entry = data
                    if 'children_urls' not in old_entry:
                        old_entry['children_urls'] = []
                    if 'content_links' not in old_entry:
                        old_entry['content_links'] = []
                    if 'valid' not in old_entry:
                        old_entry['valid'] = True  # Default to True for backward compatibility
                    return [old_entry]
                else:
                    logger.warning(f"Unknown cache format")
                    return []
        except Exception as e:
            logger.warning(f"Error loading cache: {str(e)}")
            return []
    return []


def save_urls_metadata_to_cache(urls_metadata: List[Dict[str, Any]]):
    """Save discovered URLs with metadata to cache file."""
    ensure_cache_dir()
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({'urls': urls_metadata}, f, indent=2)
        logger.info(f"Saved {len(urls_metadata)} URLs with metadata to cache")
    except Exception as e:
        logger.warning(f"Error saving cache: {str(e)}")


# Patterns to identify documentation navigation elements (used as fallback for sidebar extraction)
NAV_SELECTORS = [
    'nav a',  # Navigation links
    '.sidebar a',  # Sidebar links
    '.navigation a',  # Navigation class
    '[role="navigation"] a',  # ARIA navigation
    '.docs-nav a',  # Docs-specific navigation
    '.menu a',  # Menu links
]


async def is_valid_docs_url(url: str) -> bool:
    """
    Check if URL is a valid documentation page.
    
    Args:
        url: The URL to validate (should be normalized before calling)
        
    Returns:
        True if URL is a valid documentation page, False otherwise
    """
    if not url:
        return False
    
    # Must be a memgraph.com/docs URL
    if 'memgraph.com/docs' not in url:
        return False
    
    # Skip the base domain without /docs path
    if url.rstrip('/') == 'https://memgraph.com' or url.rstrip('/') == 'http://memgraph.com':
        return False
    
    # Skip common non-content URLs
    skip_patterns = [
        '/search',           # Search pages
        '/api/',             # API endpoints (not documentation)
        '.pdf',              # PDF files
        '.zip',              # ZIP archives
        '.tar.gz',           # Compressed archives
        'mailto:',           # Email links
        'javascript:',       # JavaScript pseudo-protocol
    ]
    
    url_lower = url.lower()
    for pattern in skip_patterns:
        if pattern in url_lower:
            return False
    
    # Additional checks for specific invalid patterns
    # Skip URLs that are just fragments or query params
    if url.startswith('#') or url.startswith('?'):
        return False
    
    # Must be a valid docs page
    return True


async def normalize_url(url: str) -> str:
    """Normalize URL by removing fragments and query params."""
    # Remove fragment
    url = url.split('#')[0]
    # Remove query params (but keep path)
    if '?' in url:
        base, _ = url.split('?', 1)
        # Only remove query if it's not essential
        if 'page=' not in url.lower() and 'offset=' not in url.lower():
            url = base
    return url.rstrip('/')


async def extract_sidebar_links(soup: BeautifulSoup) -> List[str]:
    """Extract sidebar links from the base documentation page (only called once)."""
    found_links = set()
    
    # Extract links from aside/sidebar element
    aside_elements = soup.find_all('aside')
    for aside in aside_elements:
        try:
            for link in aside.find_all('a', href=True):
                href = link.get('href', '')
                if href:
                    # Convert to absolute URL
                    if href.startswith('/docs'):
                        full_url = f"https://memgraph.com{href}"
                    elif href.startswith('/'):
                        # Skip non-docs root links
                        continue
                    elif href.startswith('http') and 'memgraph.com/docs' in href:
                        full_url = href
                    else:
                        continue

                    full_url = await normalize_url(full_url)
                    if await is_valid_docs_url(full_url):
                        found_links.add(full_url)
        except Exception as e:
            logger.debug(f"Error extracting links from aside: {str(e)}")

    # Try other navigation/sidebar selectors as fallback
    if not found_links:
        for selector in NAV_SELECTORS:
            try:
                for link in soup.select(selector):
                    href = link.get('href', '')
                    if href:
                        # Convert to absolute URL
                        if href.startswith('/docs'):
                            full_url = f"https://memgraph.com{href}"
                        elif href.startswith('/'):
                            # Skip non-docs root links
                            continue
                        elif href.startswith('http') and 'memgraph.com/docs' in href:
                            full_url = href
                        else:
                            continue

                        full_url = await normalize_url(full_url)
                        if await is_valid_docs_url(full_url):
                            found_links.add(full_url)
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {str(e)}")

    return list(found_links)


async def extract_content_links(soup: BeautifulSoup) -> List[str]:
    """Extract documentation links from main content text (not sidebar/navigation)."""
    found_links = set()
    
    # Extract text content from nested <main> inside outer <main> tag
    outer_main = soup.find('main')
    if not outer_main:
        return []
    
    # Look for nested <main> tag inside the outer main
    inner_main = outer_main.find('main')
    if not inner_main:
        # If no nested main, use the outer main
        inner_main = outer_main
    
    # Remove scripts and styles
    for script in inner_main(["script", "style", "nav", "aside"]):
        script.decompose()
    
    # Find all links in the main content
    for link in inner_main.find_all('a', href=True):
        href = link.get('href', '')
        if href:
            # Convert to absolute URL
            if href.startswith('/docs'):
                full_url = f"https://memgraph.com{href}"
            elif href.startswith('http') and 'memgraph.com/docs' in href:
                full_url = href
            else:
                continue

            full_url = await normalize_url(full_url)
            if await is_valid_docs_url(full_url):
                found_links.add(full_url)

    return list(found_links)


async def extract_page_metadata(url: str) -> Dict[str, Any]:
    """
    Extract metadata (description and keywords) from a documentation page using LLM.

    Args:
        url: The URL of the documentation page

    Returns:
        Dictionary with keys: url, description, keywords
    """
    try:
        # Fetch the page content
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract text content from nested <main> inside outer <main> tag
            outer_main = soup.find('main')
            if not outer_main:
                raise ValueError(f"No outer <main> tag found in {url}")

            # Look for nested <main> tag inside the outer main
            inner_main = outer_main.find('main')
            if not inner_main:
                raise ValueError(f"No nested <main> tag found inside outer <main> in {url}")

            # Remove scripts and styles from inner main content
            for script in inner_main(["script", "style"]):
                script.decompose()
            main_content = inner_main.get_text(separator='\n', strip=True)

            # Limit content size to avoid token limits (keep first 8000 chars for metadata extraction)
            if len(main_content) > 8000:
                main_content = main_content[:8000] + "..."

            # Extract page title
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()

            # Prepare prompt for LLM
            prompt = f"""Extract metadata from the following Memgraph documentation page.

URL: {url}
Title: {title}

Page Content:
{main_content}

Please provide:
1. description: A concise 1-2 sentence description of what this page covers
2. keywords: A comma-separated list of relevant keywords and concepts (3-5 keywords)

Return ONLY a valid JSON object in this format:
{{
  "description": "Brief description of the page content",
  "keywords": "keyword1, keyword2, keyword3, memgraph, cypher"
}}

Focus on technical terms, Memgraph features, Cypher concepts, and the main topics covered."""

            # Call OpenAI API
            client = get_openai_client()
            model = os.getenv("CHAT_MODEL", "gpt-4o")

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts metadata from documentation pages. Always return valid JSON with 'description' and 'keywords' fields."
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

            # Ensure we have required fields
            description = result.get("description", "")
            keywords = result.get("keywords", "")

            logger.info(f"Extracted metadata from {url}")
            return {
                "url": url,
                "description": description,
                "keywords": keywords,
                "children_urls": [],  # Will be populated during discovery (from sidebar)
                "content_links": [],  # Links found in main content text
                "valid": True
            }

    except Exception as e:
        logger.error(f"Error extracting metadata from {url}: {str(e)}", exc_info=True)
        return {
            "url": url,
            "description": "",
            "keywords": "",
            "children_urls": [],
            "content_links": [],
            "valid": False
        }


async def discover_documentation_urls_stream():
    """
    Generator that yields URL metadata as URLs are discovered.
    Always uses cache if available, otherwise discovers URLs fresh.
    Always extracts metadata for each URL.

    Yields:
        Dictionary with keys: url, description, keywords, children_urls, content_links
    """
    # Check cache first - if available, use it
    cached_urls_metadata = load_cached_urls_metadata()
    if cached_urls_metadata:
        logger.info(f"Using {len(cached_urls_metadata)} cached URLs with metadata")
        for url_metadata in cached_urls_metadata:
            yield url_metadata
        return
    
    urls_metadata = []
    visited = set()
    seen_urls = set()  # Track normalized URLs to avoid duplicates
    url_to_metadata = {}  # Map URL to its metadata dict for updating children_urls
    to_visit = deque()  # Will be populated with base URL and sidebar links

    # Extract sidebar links once from base URL
    sidebar_links = []
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            logger.info(f"Extracting sidebar links from base URL: {MEMGRAPH_DOCS_BASE_URL}")
            response = await client.get(MEMGRAPH_DOCS_BASE_URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            sidebar_links = await extract_sidebar_links(soup)
            logger.info(f"Extracted {len(sidebar_links)} sidebar links from base URL")
        except Exception as e:
            logger.warning(f"Error extracting sidebar links from base URL: {str(e)}")
            # Continue without sidebar links if extraction fails

    # Use queue-based BFS instead of recursion
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Add base URL to queue first
        base_url_normalized = await normalize_url(MEMGRAPH_DOCS_BASE_URL)
        seen_urls.add(base_url_normalized)
        to_visit.append(MEMGRAPH_DOCS_BASE_URL)
        
        # Add all sidebar links to the queue
        for sidebar_link in sidebar_links:
            normalized = await normalize_url(sidebar_link)
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                to_visit.append(sidebar_link)
        
        while to_visit:
            url = to_visit.popleft()

            # Skip if already visited
            if url in visited:
                continue

            visited.add(url)

            try:
                logger.info(f"Scraping page: {url}")
                response = await client.get(url)
                response.raise_for_status()

                # Only process HTML pages
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    logger.debug(f"Skipping non-HTML content: {url}")
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract content links from main content (not sidebar)
                content_links = await extract_content_links(soup)

                # Get or create metadata for current URL (parent)
                if url not in url_to_metadata:
                    logger.info(f"Extracting metadata for: {url}")
                    parent_metadata = await extract_page_metadata(url)
                    url_to_metadata[url] = parent_metadata
                    urls_metadata.append(parent_metadata)
                    # Yield parent metadata when first discovered
                    yield parent_metadata
                else:
                    parent_metadata = url_to_metadata[url]

                # Set content links for this page
                parent_metadata["content_links"] = content_links

                # Track children URLs: base URL gets sidebar links, others get content links
                is_base_url = url == MEMGRAPH_DOCS_BASE_URL or url == f"{MEMGRAPH_DOCS_BASE_URL}/"
                if is_base_url:
                    # Base URL gets sidebar links as children
                    children_urls = sidebar_links.copy()
                else:
                    # Other pages get content links as children
                    children_urls = content_links.copy()

                # Add found content links to queue and results
                for link_url in content_links:
                    # Normalize URL for comparison
                    normalized = await normalize_url(link_url)
                    
                    if link_url not in visited:
                        if normalized not in seen_urls:
                            seen_urls.add(normalized)
                            logger.info(f"Found documentation page from content: {link_url}")

                            # Extract metadata for the URL
                            logger.info(f"Extracting metadata for: {link_url}")
                            metadata = await extract_page_metadata(link_url)
                            url_to_metadata[link_url] = metadata
                            urls_metadata.append(metadata)
                            # Yield the metadata as it's discovered
                            yield metadata

                        # Add to queue for further exploration
                        to_visit.append(link_url)

                # Update parent metadata with children URLs
                parent_metadata["children_urls"] = children_urls

            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error scraping {url}: {e.response.status_code}")
            except httpx.TimeoutException:
                logger.warning(f"Timeout scraping {url}")
            except Exception as e:
                logger.warning(f"Error scraping {url}: {str(e)}")

    logger.info(f"Discovered {len(urls_metadata)} unique documentation pages with metadata")

    # Save discovered URLs with metadata to cache
    if urls_metadata:
        save_urls_metadata_to_cache(urls_metadata)
    
    # Note: Async generators cannot return values, they just end naturally


async def discover_documentation_urls() -> List[Dict[str, Any]]:
    """
    Discover all documentation URLs from memgraph.com/docs with metadata.
    Returns a list of all discovered URL metadata dictionaries.
    Uses the streaming version internally and collects all metadata.
    """
    urls_metadata = []
    async for url_metadata in discover_documentation_urls_stream():
        urls_metadata.append(url_metadata)
    return urls_metadata

