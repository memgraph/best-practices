"""
Data models for documentation ingestion.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class SidebarUrl:
    """Represents a URL in the sidebar hierarchy."""
    url: str
    children_urls: List[str]


@dataclass
class CypherQuery:
    """Represents a Cypher query extracted from documentation."""
    entity_id: str
    query: str
    description: str


@dataclass
class DocumentationUrl:
    """Represents a documentation URL with its content links."""
    url: str
    content_urls: List[str]

