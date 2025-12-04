# Memgraph Assistant

A documentation-aware chat assistant for Memgraph that can understand the documentation and perform operations on the graph database.

## Features

- **Documentation Ingestion**: Automatically scrapes and ingests all documentation from memgraph.com/docs
- **Chat Assistant**: AI-powered wizard that understands the documentation and can help with graph operations
- **Graph Operations**: Perform queries, create nodes, relationships, and more based on documentation knowledge
- **Streaming Responses**: Real-time updates during chat interactions
- **Session Management**: Maintains conversation context across multiple interactions

## Prerequisites

- Docker and Docker Compose
- Python 3.13+ with `uv` package manager
- Node.js and npm
- OpenAI API key

## Setup

### 1. Start Services

Run Memgraph and MCP using Docker Compose:

```bash
docker compose up -d
```

This will start:
- Memgraph database on port 7687
- MCP-Memgraph server on port 8001

### 2. Backend Setup

1. Navigate to the `backend` directory
2. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   MCP_MEMGRAPH_URL=http://localhost:8001/mcp
   ```
3. Set up the environment:
   ```bash
   cd backend
   uv venv
   uv sync
   ```
4. Run the backend server:
   ```bash
   uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### 3. Frontend Setup

1. Navigate to the `frontend` directory
2. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at http://localhost:3000

## Usage

### Ingest Documentation

1. Open the frontend application (http://localhost:3000)
2. Navigate to the "Ingest Documentation" tab
3. Click "Scrape Memgraph Documentation" to automatically discover and ingest all documentation pages from memgraph.com/docs
4. Wait for ingestion to complete (this may take several minutes depending on the number of pages)

The ingestion process will:
- Discover all documentation URLs from memgraph.com/docs
- Scrape and process each page
- Create chunks and relationships in the graph
- Compute embeddings for vector search

### Use the Chat Assistant

1. Navigate to the "Chat Assistant" tab
2. Ask questions about Memgraph, such as:
   - "How do I create a node in Memgraph?"
   - "What is the syntax for MATCH queries?"
   - "Show me how to use relationships"
3. Request graph operations:
   - "Create a Person node with name 'Alice'"
   - "Find all nodes connected to node 123"
   - "Show me the graph schema"
4. The assistant will use its knowledge of the documentation to help you

## Architecture

- **Backend**: FastAPI application with:
  - `/api/ingest/scrape-all` - Scrapes and ingests all documentation
  - `/api/chat/query` - Non-streaming chat endpoint
  - `/api/chat/query-stream` - Streaming chat endpoint (SSE)
  - `/api/mcp/*` - MCP testing endpoints

- **Frontend**: Vue.js application with:
  - Ingestion interface
  - Chat interface with streaming support
  - Tool call visualization

- **Database**: Memgraph graph database storing:
  - Documentation chunks as :Chunk nodes
  - Relationships between chunks
  - Vector embeddings for semantic search

- **MCP**: Model Context Protocol server for graph operations

## API Endpoints

### Ingestion
- `POST /api/ingest/scrape-all` - Scrape and ingest all documentation
- `POST /api/ingest/discover` - Discover documentation URLs without ingesting
- `POST /api/ingest` - Ingest specific URLs

### Chat
- `POST /api/chat/query` - Chat with the assistant (non-streaming)
- `POST /api/chat/query-stream` - Chat with the assistant (streaming SSE)

### MCP
- `GET /api/mcp/test` - Test MCP connection
- `GET /api/mcp/tools` - List available MCP tools
- `POST /api/mcp/call` - Call an MCP tool

## Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `MCP_MEMGRAPH_URL` - MCP server URL (default: http://localhost:8001/mcp)
- `LOG_LEVEL` - Logging level (default: DEBUG)
- `CHAT_MODEL` - Model to use for chat (default: gpt-4o)

## Notes

- The first ingestion may take 10-30 minutes depending on the number of documentation pages
- The chat assistant maintains conversation context using sessions
- All queries are cached to prevent duplicate executions
- The assistant can perform both read and write operations on the graph

