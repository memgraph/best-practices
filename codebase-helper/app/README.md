# Memgraph Codebase Helper

Browser chat app that wraps the Claude Agent SDK (same runtime as Claude Code)
and points it at local clones of the Memgraph org's main repos:

- [`memgraph/memgraph`](https://github.com/memgraph/memgraph) — core C++ database
- [`memgraph/helm-charts`](https://github.com/memgraph/helm-charts) — Kubernetes deployment
- [`memgraph/ai-toolkit`](https://github.com/memgraph/ai-toolkit) — GraphRAG / LangChain / MCP / LlamaIndex integrations

Ask it anything about how any of them works — the agent uses `Read`, `Grep`,
and `Glob` against the checkouts to answer with concrete file / line
references, just like Claude Code does in a terminal.

## Layout

```
app/
├── .env            # your local ANTHROPIC_API_KEY (copy from .env.example)
├── backend/
│   ├── main.py             # FastAPI + SSE streaming + agent runtime
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── index.html          # chat UI (vanilla + Tailwind CDN)
    ├── app.js
    ├── styles.css
    └── nginx.conf
```

On every startup the backend clones any missing repos and pulls each one
to the tip of its tracked branch, so the agent always sees fresh code.
Checkouts live in a persistent Docker volume (`memgraph-repos`) under
Docker, or in `backend/repos/` when run locally.

## Setup

```bash
cd agents/memgraph-codebase-helper/app
cp .env.example .env      # then add your ANTHROPIC_API_KEY
```

## Run with Docker (recommended)

```bash
cd agents/memgraph-codebase-helper/app
docker compose up --build
```

Open <http://localhost:3001>. The `frontend` service (nginx) serves the UI
and proxies `/api/*` to the `backend` service (FastAPI + Claude Agent SDK).
First startup clones all three repos into a named volume
(`memgraph-repos`); every subsequent startup just pulls the latest on each
tracked branch.

To stop: `docker compose down`. To wipe the checkouts too:
`docker compose down -v`.

## Run locally (without Docker)

```bash
cd agents/memgraph-codebase-helper/app
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# claude-agent-sdk spawns the Claude Code CLI under the hood, install it once:
npm install -g @anthropic-ai/claude-code

python3 backend/main.py
```

Open <http://localhost:8001> — in dev the FastAPI server serves both the API
and the static frontend on the same port. Repos are cloned into
`backend/repos/` on first run and pulled on every subsequent startup.

## How it works

- On startup, `backend/main.py` makes sure every repo listed in `REPOS` is
  present in `REPO_ROOT`, cloning if missing and otherwise hard-resetting to
  `origin/<branch>` so the code is always current.
- The agent is created with `REPO_ROOT` as its `cwd` and with `Read`, `Grep`,
  `Glob`, and `Bash` tools enabled — the standard set Claude Code uses for
  codebase exploration. Because cwd is the parent of all three repos, a
  single Grep can search across them.
- Each chat session is a `ClaudeSDKClient` kept in memory (keyed by a
  browser-side UUID) so follow-up questions retain context. "New chat"
  resets it.
- Responses stream to the browser over Server-Sent Events. Text, tool calls,
  and tool results are rendered as separate UI elements.

## Refreshing the checkouts

Restart the backend — `docker compose restart backend` or re-running
`python3 backend/main.py` — and every repo is pulled to `HEAD` before the
server comes up.
