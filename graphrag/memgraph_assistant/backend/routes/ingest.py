"""
Ingestion endpoints for scraping and processing Memgraph documentation.
"""
import os
import json
import logging
import sys
import re
from typing import List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx
from bs4 import BeautifulSoup
import json
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unstructured2graph import from_unstructured, make_chunks, compute_embeddings
from resources import initialize_resources

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Base URL for Memgraph documentation
MEMGRAPH_DOCS_BASE_URL = "https://memgraph.com/docs"

# Cache file for discovered URLs
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "discovered_urls.json")


def ensure_cache_dir():
    """Ensure the cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_cached_urls() -> List[str]:
    """Load cached URLs from file if it exists."""
    ensure_cache_dir()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                urls = data.get('urls', [])
                logger.info(f"Loaded {len(urls)} URLs from cache")
                return urls
        except Exception as e:
            logger.warning(f"Error loading cache: {str(e)}")
            return []
    return []


def save_urls_to_cache(urls: List[str]):
    """Save discovered URLs to cache file."""
    ensure_cache_dir()
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({'urls': urls}, f, indent=2)
        logger.info(f"Saved {len(urls)} URLs to cache")
    except Exception as e:
        logger.warning(f"Error saving cache: {str(e)}")


async def discover_documentation_urls_stream(use_cache: bool = True, force_refresh: bool = False):
    """
    Generator that yields URLs as they are discovered.
    
    Args:
        use_cache: If True, check cache first and use cached URLs if available
        force_refresh: If True, ignore cache and scrape fresh URLs
    """
    from collections import deque
    
    # Check cache first if enabled and not forcing refresh
    if use_cache and not force_refresh:
        cached_urls = load_cached_urls()
        if cached_urls:
            logger.info(f"Using {len(cached_urls)} cached URLs")
            for url in cached_urls:
                yield url
            return
    
    urls = []
    visited = set()
    seen_urls = set()  # Track normalized URLs to avoid duplicates
    to_visit = deque([(MEMGRAPH_DOCS_BASE_URL, 0)])  # (url, depth)
    max_depth = 15
    
    # Patterns to identify documentation navigation elements
    nav_selectors = [
        'nav a',  # Navigation links
        '.sidebar a',  # Sidebar links
        '.navigation a',  # Navigation class
        '[role="navigation"] a',  # ARIA navigation
        '.docs-nav a',  # Docs-specific navigation
        '.menu a',  # Menu links
        'aside a',  # Aside/sidebar
    ]
    
    # Patterns to identify content links
    content_selectors = [
        'article a',
        '.content a',
        'main a',
        '.docs-content a',
    ]
    
    async def is_valid_docs_url(url: str) -> bool:
        """Check if URL is a valid documentation page."""
        if not url or 'memgraph.com/docs' not in url:
            return False
        
        # Skip common non-content URLs
        skip_patterns = [
            '/search',
            '/api/',
            '.pdf',
            '.zip',
            '.tar.gz',
            'mailto:',
            'javascript:',
            '#',
        ]
        
        for pattern in skip_patterns:
            if pattern in url.lower():
                return False
        
        # Must be a docs page
        return 'memgraph.com/docs' in url
    
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
    
    async def extract_links_from_page(soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract documentation links from a page."""
        found_links = set()
        
        # First, try to find navigation/sidebar links (higher priority)
        for selector in nav_selectors:
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
        
        # Then, find content links (lower priority, but still useful)
        for selector in content_selectors:
            try:
                for link in soup.select(selector):
                    href = link.get('href', '')
                    if href:
                        if href.startswith('/docs'):
                            full_url = f"https://memgraph.com{href}"
                        elif href.startswith('http') and 'memgraph.com/docs' in href:
                            full_url = href
                        else:
                            continue
                        
                        full_url = await normalize_url(full_url)
                        if await is_valid_docs_url(full_url):
                            found_links.add(full_url)
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {str(e)}")
        
        # Fallback: find all links if selectors didn't work
        if not found_links:
            for link in soup.find_all('a', href=True):
                href = link['href']
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
    
    # Use queue-based BFS instead of recursion
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        while to_visit:
            url, depth = to_visit.popleft()
            
            # Skip if already visited or too deep
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            
            try:
                logger.info(f"Scraping page (depth {depth}): {url}")
                response = await client.get(url)
                response.raise_for_status()
                
                # Only process HTML pages
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    logger.debug(f"Skipping non-HTML content: {url}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract links from this page
                found_links = await extract_links_from_page(soup, url)
                
                # Add found links to queue and results
                for link_url in found_links:
                    if link_url not in visited:
                        # Normalize and check for duplicates
                        normalized = await normalize_url(link_url)
                        if normalized not in seen_urls:
                            seen_urls.add(normalized)
                            urls.append(link_url)
                            logger.info(f"Found documentation page: {link_url}")
                            # Yield the URL as it's discovered
                            yield link_url
                        
                        # Add to queue for further exploration (use original URL for queue)
                        if depth < max_depth:
                            to_visit.append((link_url, depth + 1))
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error scraping {url}: {e.response.status_code}")
            except httpx.TimeoutException:
                logger.warning(f"Timeout scraping {url}")
            except Exception as e:
                logger.warning(f"Error scraping {url}: {str(e)}")
    
    logger.info(f"Discovered {len(urls)} unique documentation pages")
    
    # Save discovered URLs to cache
    if urls:
        save_urls_to_cache(urls)
    
    # Note: Async generators cannot return values, they just end naturally


async def discover_documentation_urls() -> List[str]:
    """
    Discover all documentation URLs from memgraph.com/docs.
    Returns a list of all discovered URLs.
    Uses the streaming version internally and collects all URLs.
    """
    urls = []
    async for url in discover_documentation_urls_stream():
        urls.append(url)
    return urls


@router.post("/discover")
async def discover_docs(request: Request):
    """
    Discover all documentation URLs from memgraph.com/docs.
    Returns a list of URLs that can be ingested.
    
    Optional JSON body:
    {
        "force_refresh": false  # If true, ignore cache and scrape fresh URLs
    }
    """
    try:
        try:
            body = await request.json()
            force_refresh = body.get("force_refresh", False)
        except:
            force_refresh = False
        
        urls = []
        async for url in discover_documentation_urls_stream(use_cache=True, force_refresh=force_refresh):
            urls.append(url)
        
        return {
            "urls": urls,
            "count": len(urls),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error discovering documentation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error discovering documentation: {str(e)}"
        )


@router.post("/discover-stream")
async def discover_docs_stream(request: Request):
    """
    Discover all documentation URLs from memgraph.com/docs with streaming.
    Streams URLs as they are discovered via Server-Sent Events (SSE).
    
    Optional JSON body:
    {
        "force_refresh": false  # If true, ignore cache and scrape fresh URLs
    }
    """
    try:
        body = await request.json()
        force_refresh = body.get("force_refresh", False)
    except:
        force_refresh = False
    
    async def event_generator():
        """Generator function for SSE events."""
        urls = []
        
        try:
            async for url in discover_documentation_urls_stream(use_cache=True, force_refresh=force_refresh):
                urls.append(url)
                yield f"data: {json.dumps({'type': 'url', 'url': url, 'count': len(urls)})}\n\n"
            
            # Send completion message
            yield f"data: {json.dumps({'type': 'complete', 'total_count': len(urls)})}\n\n"
        
        except Exception as e:
            logger.error(f"Error in streaming discovery: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/scrape-all")
async def scrape_all_docs():
    """
    Automatically discover and ingest all documentation from memgraph.com/docs.
    """
    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key."
        )

    try:
        # Discover all documentation URLs
        logger.info("Discovering documentation URLs...")
        urls = await discover_documentation_urls()
        
        if not urls:
            raise HTTPException(
                status_code=500,
                detail="No documentation URLs discovered. Please check the discovery endpoint."
            )
        
        logger.info(f"Processing {len(urls)} documentation pages. Starting ingestion...")

        # Initialize resources once at the beginning (with cleanup)
        memgraph, lightrag_wrapper = await initialize_resources(
            cleanup=True, 
            create_vector_index=True
        )

        # Process documents one by one - from_unstructured called once per URL
        for idx, url in enumerate(urls, 1):
            logger.info(f"Processing document {idx}/{len(urls)}: {url}")

            # Ingest single document
            await from_unstructured(
                [url],
                memgraph,
                lightrag_wrapper,
                only_chunks=False,
                link_chunks=True,
            )

        # Create vector index and compute embeddings after all documents are ingested
        logger.info("Creating vector search index and computing embeddings...")
        try:
            compute_embeddings(memgraph, "Chunk")
            logger.info("Successfully created vector index and computed embeddings")
        except Exception as e:
            logger.warning(f"Error creating vector index or computing embeddings: {str(e)}")

        logger.info("Successfully ingested all documentation pages into Memgraph!")

        return {
            "message": "Successfully ingested all documentation pages into Memgraph!",
            "urls_processed": len(urls),
            "urls": urls[:10],  # Return first 10 as sample
            "status": "completed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during ingestion: {str(e)}"
        )


@router.post("")
async def ingest_documents(request: Request):
    """
    Ingest unstructured documents from URLs into Memgraph.
    
    Expected JSON body:
    {
        "urls": ["url1", "url2", ...],
        "only_chunks": false,
        "link_chunks": true,
        "create_vector_index": true,
        "cleanup": true
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
    only_chunks = body.get("only_chunks", False)
    link_chunks = body.get("link_chunks", True)
    create_vector_index = body.get("create_vector_index", True)
    cleanup = body.get("cleanup", True)
    
    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key."
        )

    if not urls or not isinstance(urls, list):
        raise HTTPException(
            status_code=400,
            detail="No URLs provided. Please provide at least one URL in the 'urls' array."
        )

    try:
        logger.info(f"Processing {len(urls)} documentation pages. Starting ingestion...")

        memgraph, lightrag_wrapper = await initialize_resources(
            cleanup=cleanup, 
            create_vector_index=create_vector_index
        )

        # Ingest documents
        await from_unstructured(
            urls,
            memgraph,
            lightrag_wrapper,
            only_chunks=only_chunks,
            link_chunks=link_chunks,
        )

        # Create vector index and compute embeddings if requested
        if create_vector_index:
            logger.info("Creating vector search index and computing embeddings...")
            try:
                compute_embeddings(memgraph, "Chunk")
                logger.info("Successfully created vector index and computed embeddings")
            except Exception as e:
                logger.warning(f"Error creating vector index or computing embeddings: {str(e)}")

        logger.info("Successfully ingested all documentation pages into Memgraph!")

        return {
            "message": "Successfully ingested all documentation pages into Memgraph!",
            "urls_processed": len(urls),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during ingestion: {str(e)}"
        )


@router.post("/single")
async def ingest_single_document(request: Request):
    """
    Ingest a single document from a URL into Memgraph.
    Useful for progress tracking - process one document at a time.
    
    Expected JSON body:
    {
        "url": "https://example.com/doc",
        "only_chunks": false,
        "link_chunks": true,
        "create_vector_index": true,
        "cleanup": false  # Usually false for single document ingestion
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
    url = body.get("url")
    only_chunks = body.get("only_chunks", False)
    link_chunks = body.get("link_chunks", True)
    create_vector_index = body.get("create_vector_index", True)
    cleanup = body.get("cleanup", False)
    
    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key."
        )

    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=400,
            detail="No URL provided. Please provide a 'url' string."
        )

    try:
        logger.info(f"Processing single document: {url}")

        memgraph, lightrag_wrapper = await initialize_resources(cleanup=cleanup, create_vector_index=create_vector_index)

        # Ingest single document
        await from_unstructured(
            [url],
            memgraph,
            lightrag_wrapper,
            only_chunks=only_chunks,
            link_chunks=link_chunks,
        )

        # Create vector index and compute embeddings if requested
        if create_vector_index:
            logger.info("Computing embeddings and creating vector search index...")
            try:
                # Compute embeddings for all chunks (including newly added ones)
                compute_embeddings(memgraph, "Chunk")
                logger.info("Successfully computed embeddings and created vector index")
            except Exception as e:
                logger.warning(f"Error computing embeddings or creating vector index: {str(e)}")

        logger.info(f"Successfully ingested document: {url}")

        return {
            "message": f"Successfully ingested document: {url}",
            "url": url,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during ingestion: {str(e)}"
        )


@router.post("/batch")
async def ingest_batch_documents(request: Request):
    """
    Ingest multiple documents from URLs into Memgraph.
    Processes documents one by one and returns success when all are done.
    
    Expected JSON body:
    {
        "urls": ["url1", "url2", ...],
        "only_chunks": false,
        "link_chunks": true,
        "create_vector_index": true,
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
    only_chunks = body.get("only_chunks", False)
    link_chunks = body.get("link_chunks", True)
    create_vector_index = body.get("create_vector_index", True)
    cleanup = body.get("cleanup", False)
    
    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key."
        )

    if not urls or not isinstance(urls, list):
        raise HTTPException(
            status_code=400,
            detail="No URLs provided. Please provide at least one URL in the 'urls' array."
        )

    try:
        logger.info(f"Processing batch of {len(urls)} documents. Starting ingestion...")

        # Initialize resources once at the beginning (with cleanup and vector index if requested)
        memgraph, lightrag_wrapper = await initialize_resources(
            cleanup=cleanup, 
            create_vector_index=create_vector_index
        )

        # Process documents one by one - from_unstructured called once per URL
        for idx, url in enumerate(urls, 1):
            logger.info(f"Processing document {idx}/{len(urls)}: {url}")

            # Ingest single document
            await from_unstructured(
                [url],
                memgraph,
                lightrag_wrapper,
                only_chunks=only_chunks,
                link_chunks=link_chunks,
            )

        # Compute embeddings after all documents are ingested (index is already created by initialize_resources)
        if create_vector_index:
            logger.info("Computing embeddings for all chunks...")
            try:
                compute_embeddings(memgraph, "Chunk")
                logger.info("Successfully computed embeddings")
            except Exception as e:
                logger.warning(f"Error computing embeddings: {str(e)}")

        logger.info(f"Successfully ingested all {len(urls)} documents into Memgraph!")

        return {
            "message": f"Successfully ingested {len(urls)} document(s) into Memgraph!",
            "urls_processed": len(urls),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error during batch ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during batch ingestion: {str(e)}"
        )


@router.post("/estimate")
async def estimate_ingestion(request: Request):
    """
    Estimate the number of chunks and processing time for given URLs.
    Returns chunk count per document and total estimated time (10 seconds per chunk).
    
    Expected JSON body:
    {
        "urls": ["url1", "url2", ...]
    }
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    
    urls = body.get("urls", [])
    
    if not urls or not isinstance(urls, list):
        raise HTTPException(
            status_code=400,
            detail="No URLs provided. Please provide at least one URL in the 'urls' array."
        )
    
    try:
        # Get chunk estimates without full processing
        chunked_documents = make_chunks(urls)
        
        estimates = []
        total_chunks = 0
        
        for doc in chunked_documents:
            chunk_count = len(doc.chunks)
            total_chunks += chunk_count
            estimated_time = chunk_count * 10  # 10 seconds per chunk
            
            estimates.append({
                "url": str(doc.source),
                "chunk_count": chunk_count,
                "estimated_time_seconds": estimated_time
            })
        
        total_estimated_time = total_chunks * 10
        
        return {
            "total_chunks": total_chunks,
            "total_estimated_time_seconds": total_estimated_time,
            "documents": estimates
        }
    
    except Exception as e:
        logger.error(f"Error estimating ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error estimating ingestion: {str(e)}"
        )

