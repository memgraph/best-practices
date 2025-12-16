"""
Sidebar processing functionality for scraping Memgraph documentation sidebar structure.
"""
import logging
from typing import List, Dict
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from scrape_urls import (
    normalize_url,
    is_valid_docs_url,
    MEMGRAPH_DOCS_BASE_URL
)
from models import SidebarUrl

logger = logging.getLogger(__name__)


async def discover_sidebar_elements() -> List[SidebarUrl]:
    """
    Discover sidebar elements from the main documentation page.
    The sidebar structure has <a> elements followed by <div> elements containing children.
    
    Returns:
        List of SidebarUrl objects with url and children_urls
    """
    logger.info(f"Discovering sidebar elements from {MEMGRAPH_DOCS_BASE_URL}")
    
    sidebar_urls: Dict[str, List[str]] = {}
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(MEMGRAPH_DOCS_BASE_URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the aside element (there's only one)
            aside = soup.find('aside')
            if not aside:
                raise ValueError("No sidebar element found in documentation page")
            
            # Find all <a> elements in the sidebar
            for link in aside.find_all('a', href=True):
                href = link.get('href', '')
                if not href:
                    continue
                
                parent_url = normalize_url(urljoin(MEMGRAPH_DOCS_BASE_URL, href))
                if not is_valid_docs_url(parent_url):
                    continue
                
                # Initialize children list
                if parent_url not in sidebar_urls:
                    sidebar_urls[parent_url] = []
                
                # Structure: div -> div -> ul -> li -> a
                next_div = link.find_next_sibling('div')
                ul = next_div and next_div.find('div') and next_div.find('div').find('ul')
                if not ul:
                    continue
                
                children = []
                for li in ul.find_all('li', recursive=False):
                    a = li.find('a', href=True)
                    if a and a.get('href'):
                        url = normalize_url(urljoin(MEMGRAPH_DOCS_BASE_URL, a['href']))
                        if is_valid_docs_url(url):
                            children.append(url)
                
                sidebar_urls[parent_url] = sorted(children)
            
        except Exception as e:
            logger.warning(f"Error processing sidebar from {MEMGRAPH_DOCS_BASE_URL}: {str(e)}")
    
    # Convert to SidebarUrl objects
    result = [
        SidebarUrl(url=url, children_urls=children)
        for url, children in sidebar_urls.items()
    ]
    
    logger.info(f"Processed {len(result)} sidebar URLs")
    return result

