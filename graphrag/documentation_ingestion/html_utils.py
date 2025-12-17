"""
HTML parsing utilities for extracting content from documentation pages.
"""
from typing import Any
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def get_cleaned_inner_main(soup: BeautifulSoup, require_nested: bool = False) -> Any:
    """
    Get the inner main content area, cleaned of navigation and script elements.
    
    Args:
        soup: BeautifulSoup object of the page
        require_nested: If True, raises ValueError if no nested <main> tag found
        
    Returns:
        BeautifulSoup element containing the main content
    """
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


def extract_markdown_content(soup: BeautifulSoup) -> str:
    """Extract content as markdown from a BeautifulSoup object."""
    inner_main = get_cleaned_inner_main(soup, require_nested=False)
    return md(str(inner_main), heading_style="ATX", strip=['script', 'style'])

