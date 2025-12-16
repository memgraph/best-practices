# Documentation Ingestion Script

## Goal

Ingest Memgraph documentation from `memgraph.com/docs` and create a knowledge graph that combines:
- **Unstructured chunks** from the documentation pages
- **Knowledge graph construction** with entities and relationships extracted from the content
- **Cypher query extraction** to identify and store Cypher queries found in the documentation

## Installation

Install dependencies using `uv`:

```bash
uv sync
```

## Usage

Run the script using `uv`:

```bash
uv run scrape_docs.py
```

### Command-Line Options

```bash
uv run scrape_docs.py [OPTIONS]
```

**Options:**

- `--cleanup`: Clean up existing data before ingestion (drops all graph data)
- `--skip-processed`: Skip URLs that have already been processed
- `--max-urls N`: Limit processing to first N URLs (useful for testing)

### Examples

**Clean start (drop existing data and re-ingest everything):**
```bash
uv run scrape_docs.py --cleanup
```

**Test with first 10 URLs:**
```bash
uv run scrape_docs.py --max-urls 10
```

**Skip already processed URLs:**
```bash
uv run scrape_docs.py --skip-processed
```

## Prerequisites

1. **Memgraph Database**: Make sure Memgraph is running and accessible
   - Default connection: `localhost:7687`
   - Can be configured via environment variables: `MEMGRAPH_HOST` and `MEMGRAPH_PORT`

2. **OpenAI API Key** (optional): For LLM-based keyword extraction and summarization
   - Set `OPENAI_API_KEY` environment variable
   - If not set, keywords and summaries will be empty

## How It Works

1. **URL Discovery**: 
   - Discovers all documentation URLs from `memgraph.com/docs`
   - Extracts metadata: validity, keywords, summary, content links, sidebar children
   - Caches discovered URLs for faster subsequent runs

2. **Document Processing**:
   - For each URL:
     - Fetches and parses the page content
     - Extracts unstructured chunks using `unstructured2graph`
     - Uses LightRAG to extract entities, relationships, and Cypher queries
     - Stores everything in Memgraph

3. **Knowledge Graph Construction**:
   - Creates nodes for chunks, entities, and Cypher queries
   - Links chunks together based on content relationships
   - Computes embeddings for semantic search

## Output

The script creates:
- **Knowledge Graph** in Memgraph with:
  - `Chunk` nodes: Text chunks from documents
  - `base` nodes: Entities extracted from text
  - `CypherQuery` nodes: Cypher queries found in documentation
  - Relationships: Connections between entities and chunks
  - `ProcessedUrls` nodes: Track which URLs have been processed

- **LightRAG Storage**: Directory `lightrag_storage.out/` containing:
  - KV stores for documents, entities, relationships, chunks
  - Vector databases for semantic search

- **Cache**: Directory `cache/` containing:
  - `discovered_urls.json`: Cached URL metadata

## Notes

- The script processes documents sequentially (one at a time)
- Failed URLs are logged but don't stop the entire process
- Use `--skip-processed` to resume after interruptions
- The script is designed to be idempotent (safe to run multiple times)
- URL discovery results are cached - delete `cache/discovered_urls.json` to force fresh discovery
