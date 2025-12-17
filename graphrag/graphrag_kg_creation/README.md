# Memgraph GraphRAG Demo

A demo application for creating knowledge graphs using Memgraph and GraphRAG.

## Prerequisites

- Docker and Docker Compose
- Python 3.x with `uv` package manager
- Node.js and npm

## Setup

### Memgraph

Run Memgraph using Docker Compose:

```bash
docker compose up
```

### Backend

1. Navigate to the `backend` directory
2. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
3. Set up the environment:
   ```bash
   uv venv
   uv add -r requirements.txt
   uv sync
   ```
4. Run the backend server:
   ```bash
   uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend

1. Navigate to the `frontend` directory
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
