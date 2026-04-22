"""FastAPI backend for the Memgraph Codebase Helper.

Wraps the Claude Agent SDK (same runtime as Claude Code) behind an SSE
streaming endpoint so engineers can ask questions about Memgraph projects
from a browser. The agent's cwd is a directory containing local clones of:

  - github.com/memgraph/memgraph        (the core C++ database)
  - github.com/memgraph/helm-charts     (Kubernetes deployment)
  - github.com/memgraph/ai-toolkit      (GraphRAG / LangChain / MCP integrations)

Every repo is pulled to the tip of its tracked branch at startup, so the
agent always starts against fresh code. It explores the code with
Read / Grep / Glob / Bash — the same toolset Claude Code uses in a terminal.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent
APP_DIR = BACKEND_DIR.parent
FRONTEND_DIR = APP_DIR / "frontend"

load_dotenv(APP_DIR / ".env")


@dataclass
class Repo:
    name: str
    url: str
    branch: str
    description: str

    @property
    def path(self) -> Path:
        return (REPO_ROOT / self.name).resolve()


REPO_ROOT = Path(
    os.environ.get("REPO_ROOT") or (BACKEND_DIR / "repos")
).resolve()

# Where per-session user-attached files live. We put this inside REPO_ROOT so
# the agent can reference attachments with short relative paths — the same
# way it references files inside the repo clones.
UPLOADS_DIR_NAME = "_uploads"
UPLOADS_DIR = REPO_ROOT / UPLOADS_DIR_NAME
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SESSION_UPLOAD_FILES = 25

REPOS: list[Repo] = [
    Repo(
        name="memgraph",
        url=os.environ.get("MEMGRAPH_REPO_URL", "https://github.com/memgraph/memgraph.git"),
        branch=os.environ.get("MEMGRAPH_REPO_BRANCH", "master"),
        description="Core Memgraph database — C++ in-memory graph database engine, query execution, storage, replication.",
    ),
    Repo(
        name="helm-charts",
        url=os.environ.get("HELM_CHARTS_REPO_URL", "https://github.com/memgraph/helm-charts.git"),
        branch=os.environ.get("HELM_CHARTS_REPO_BRANCH", "main"),
        description="Official Helm charts for deploying Memgraph (standalone, HA) on Kubernetes.",
    ),
    Repo(
        name="ai-toolkit",
        url=os.environ.get("AI_TOOLKIT_REPO_URL", "https://github.com/memgraph/ai-toolkit.git"),
        branch=os.environ.get("AI_TOOLKIT_REPO_BRANCH", "main"),
        description="Memgraph AI toolkit — GraphRAG, LangChain / LlamaIndex integrations, MCP server, and related AI tooling built on top of Memgraph.",
    ),
]


def _ensure_repos() -> None:
    """Clone any missing repos into REPO_ROOT, and pull any existing ones so
    the agent always starts against fresh code.
    """
    REPO_ROOT.mkdir(parents=True, exist_ok=True)
    for repo in REPOS:
        if (repo.path / ".git").is_dir():
            print(f"[memgraph-helper] pulling {repo.name} (branch={repo.branch})")
            try:
                subprocess.run(
                    ["git", "-C", str(repo.path), "fetch", "origin", repo.branch],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(repo.path), "checkout", repo.branch],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(repo.path), "reset", "--hard", f"origin/{repo.branch}"],
                    check=True,
                )
            except subprocess.CalledProcessError as exc:
                print(f"[memgraph-helper] WARNING: failed to update {repo.name}: {exc}")
            continue
        print(f"[memgraph-helper] cloning {repo.url} → {repo.path} (branch={repo.branch})")
        try:
            subprocess.run(
                [
                    "git", "clone",
                    "--branch", repo.branch,
                    "--single-branch",
                    repo.url,
                    str(repo.path),
                ],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print(f"[memgraph-helper] WARNING: failed to clone {repo.name}: {exc}")


def _repos_ready() -> bool:
    return all((repo.path / ".git").is_dir() for repo in REPOS)


def _repo_summary() -> str:
    return "\n".join(
        f"- **{r.name}/** — {r.description}"
        for r in REPOS
    )


SYSTEM_PROMPT = f"""You are an expert on the Memgraph codebase. Memgraph is an open-source, in-memory graph database written primarily in C++. Your job is to help engineers understand how it works by exploring local checkouts.

# Available checkouts

Your cwd is `{REPO_ROOT}`, which contains:

{_repo_summary()}

Always prefix paths with the repo name so references stay unambiguous — e.g. `memgraph/src/query/interpreter.cpp:1234` rather than `src/query/interpreter.cpp:1234`. Grep and Glob patterns should typically start with `memgraph/**`, `helm-charts/**`, or `ai-toolkit/**` to scope the search.

Match the question to the right repo: language / storage / query engine questions → `memgraph/`; Kubernetes / deployment / chart questions → `helm-charts/`; GraphRAG / LangChain / LlamaIndex / MCP questions → `ai-toolkit/`. If it's unclear, grep across all three.

# User-attached files

The user can attach ad-hoc files (e.g. their own Helm `values.yaml`, a
config snippet, a log excerpt) via the UI. When they do, their message
will start with an `[attached-files]` block listing the file paths —
these live under `{UPLOADS_DIR_NAME}/<session>/` inside your cwd. Read
them with the Read tool when they're relevant to the question. Reason
about them side-by-side with the repo code (e.g. map a `values.yaml`
setting to the helm-chart template that consumes it).

# Tooling

You have Read, Grep, Glob, and Bash available — the same toolset Claude Code uses for codebase exploration. Use them aggressively:

- **Glob** — find files by pattern (e.g. `memgraph/src/query/**/*.cpp`).
- **Grep** — find symbols, call sites, string literals. Prefer Grep over Bash + grep.
- **Read** — read specific files or ranges. Use when you already know the path.
- **Bash** — for `git log`, `git blame`, `git diff`, directory listings, or anything grep/glob can't express. Treat the checkouts as read-only — don't fetch, pull, mutate, or write to them. The backend pulls every repo to `HEAD` at startup; the code you see is already current.

# Style

- **Ground every claim in the code.** When you describe behaviour, cite concrete files with line numbers — e.g. "see `memgraph/src/query/interpreter.cpp:1234`". The UI renders these as clickable references.
- Prefer short quoted snippets over paraphrasing when the code itself is clear.
- When tracing how something works, walk the call chain: entry point → intermediate layer → leaf. Name each function and the file it lives in.
- Start with a brief orientation (2–4 sentences) before diving into code citations.
- If the user's question is ambiguous, ask one clarifying question before spelunking.
- Be honest about uncertainty — say "I couldn't find X" rather than inventing.

# Don't

- Don't dump raw file contents unless the user asks.
- Don't fabricate paths, symbol names, or line numbers. Every reference must come from a real tool call in this conversation.
- Don't modify the repos without being asked.
"""


AVAILABLE_MODELS: list[dict] = [
    {"id": "claude-haiku-4-5", "label": "Haiku 4.5 — fastest, cheapest"},
    {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6 — balanced"},
    {"id": "claude-opus-4-7", "label": "Opus 4.7 — best reasoning"},
]
_VALID_MODEL_IDS = {m["id"] for m in AVAILABLE_MODELS}


def _resolve_model(requested: str | None) -> str | None:
    if requested and requested in _VALID_MODEL_IDS:
        return requested
    env_model = os.environ.get("ANTHROPIC_MODEL")
    if env_model and env_model in _VALID_MODEL_IDS:
        return env_model
    return env_model or None  # let SDK default handle unknowns


def _agent_options(model: str | None = None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["Bash", "Read", "Grep", "Glob"],
        permission_mode="bypassPermissions",
        cwd=str(REPO_ROOT),
        model=_resolve_model(model),
    )


app = FastAPI(title="Memgraph Codebase Helper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    # "usage"          — describe user-facing behaviour only
    # "implementation" — describe the code path, classes, call chain
    # "both"           — usage first, implementation second (default)
    mode: str | None = None
    # Override the model for this session. If it differs from the model the
    # session was created with, the session is transparently recycled (a new
    # ClaudeSDKClient is created — conversation history is lost).
    model: str | None = None


MODE_DIRECTIVES: dict[str, str] = {
    "usage": (
        "\n\n[answer-mode=usage] Frame your answer from the perspective of a "
        "person **using** Memgraph. Describe the observable behaviour, how "
        "to configure / invoke / interact with the feature, and what "
        "practical outcomes it produces. Skip internal implementation "
        "details unless they directly change observable behaviour. Do NOT "
        "include a 'How it's implemented' section."
    ),
    "implementation": (
        "\n\n[answer-mode=implementation] Frame your answer around **how "
        "the code is implemented**. Walk the call chain: entry point → "
        "intermediate layer → leaf. Name the files, classes, functions, "
        "and data structures involved, with concrete file / line references "
        "(e.g. `memgraph/src/query/interpreter.cpp:1234`). Do NOT include a "
        "'How it works (usage)' section."
    ),
    "both": (
        "\n\n[answer-mode=both] Structure your answer in two sections:\n"
        "1. **How it works** — the user-facing behaviour and how to interact "
        "with it. This comes first.\n"
        "2. **How it's implemented** — the code path, call chain, and "
        "internal design, with concrete file / line references "
        "(e.g. `memgraph/src/query/interpreter.cpp:1234`)."
    ),
}


def _apply_mode(message: str, mode: str | None) -> str:
    directive = MODE_DIRECTIVES.get((mode or "both").lower(), MODE_DIRECTIVES["both"])
    return message + directive


def _sanitize_session_id(session_id: str) -> str:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:64]
    if not safe:
        raise HTTPException(400, "Invalid session_id")
    return safe


def _session_upload_dir(session_id: str, create: bool = True) -> Path:
    safe = _sanitize_session_id(session_id)
    d = UPLOADS_DIR / safe
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_filename(name: str) -> str:
    base = Path(name).name
    if not base or base in (".", ".."):
        raise HTTPException(400, "Invalid filename")
    cleaned = "".join(c if (c.isalnum() or c in "._- ") else "_" for c in base)
    cleaned = cleaned.strip().replace(" ", "_")
    return cleaned[:128] or "file"


def _list_session_uploads(session_id: str) -> list[dict]:
    d = _session_upload_dir(session_id, create=False)
    if not d.is_dir():
        return []
    files = []
    for p in sorted(d.iterdir(), key=lambda x: x.name):
        if not p.is_file():
            continue
        files.append({
            "name": p.name,
            "path": str(p.relative_to(REPO_ROOT)),
            "size": p.stat().st_size,
        })
    return files


def _attached_files_preface(session_id: str) -> str:
    files = _list_session_uploads(session_id)
    if not files:
        return ""
    lines = "\n".join(f"- `{f['path']}` ({f['size']} bytes)" for f in files)
    return (
        "[attached-files] The user has attached the following files to this "
        "conversation. Paths are relative to your cwd. Read them with the "
        "Read tool when they are relevant to the question, but do not dump "
        "their contents unless explicitly asked.\n"
        f"{lines}\n\n"
    )


_sessions: dict[str, ClaudeSDKClient] = {}
_session_locks: dict[str, asyncio.Lock] = {}
_session_models: dict[str, str | None] = {}


async def _drop_session(session_id: str) -> None:
    client = _sessions.pop(session_id, None)
    _session_locks.pop(session_id, None)
    _session_models.pop(session_id, None)
    if client is not None:
        try:
            await client.disconnect()
        except Exception:
            pass


async def _get_client(session_id: str, requested_model: str | None) -> ClaudeSDKClient:
    resolved = _resolve_model(requested_model)
    client = _sessions.get(session_id)
    if client is not None and _session_models.get(session_id) != resolved:
        # Caller asked for a different model than the one this session was
        # created with — reset and recreate.
        await _drop_session(session_id)
        client = None
    if client is None:
        client = ClaudeSDKClient(options=_agent_options(resolved))
        await client.connect()
        _sessions[session_id] = client
        _session_locks[session_id] = asyncio.Lock()
        _session_models[session_id] = resolved
    return client


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


def _events_from_message(message) -> list[dict]:
    events: list[dict] = []
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                events.append({"type": "text", "text": block.text})
            elif isinstance(block, ThinkingBlock):
                events.append({"type": "thinking", "text": block.thinking})
            elif isinstance(block, ToolUseBlock):
                events.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
    elif isinstance(message, UserMessage):
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                content = block.content
                if isinstance(content, list):
                    content = "".join(
                        getattr(b, "text", "") or str(b) for b in content
                    )
                text = str(content or "")
                if len(text) > 6000:
                    text = text[:6000] + "\n…[truncated]"
                events.append({
                    "type": "tool_result",
                    "tool_use_id": block.tool_use_id,
                    "is_error": bool(block.is_error),
                    "content": text,
                })
    elif isinstance(message, ResultMessage):
        usage = getattr(message, "usage", None) or {}

        def _u(key: str) -> int:
            if isinstance(usage, dict):
                return int(usage.get(key) or 0)
            return int(getattr(usage, key, 0) or 0)

        # Total input counts every token the model had to look at, including
        # tokens served from the prompt cache (they're cheap but still part
        # of the context window).
        input_tokens = (
            _u("input_tokens")
            + _u("cache_creation_input_tokens")
            + _u("cache_read_input_tokens")
        )
        output_tokens = _u("output_tokens")
        events.append({
            "type": "result",
            "duration_ms": message.duration_ms,
            "num_turns": message.num_turns,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
    elif isinstance(message, SystemMessage):
        pass
    return events


def _repo_head(repo: Repo) -> str | None:
    if not (repo.path / ".git").is_dir():
        return None
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo.path), "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return None


@app.get("/api/repos")
async def get_repos():
    return {
        "root": str(REPO_ROOT),
        "repos": [
            {
                "name": r.name,
                "url": r.url,
                "branch": r.branch,
                "description": r.description,
                "path": str(r.path),
                "head": _repo_head(r),
                "ready": (r.path / ".git").is_dir(),
            }
            for r in REPOS
        ],
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(500, "ANTHROPIC_API_KEY is not set. Add it to app/.env")
    if not _repos_ready():
        raise HTTPException(503, f"Repos not ready at {REPO_ROOT}. Wait for the initial clone to finish and retry.")

    session_id = req.session_id or str(uuid.uuid4())

    async def stream() -> AsyncGenerator[str, None]:
        yield _sse({"type": "session", "session_id": session_id})
        try:
            client = await _get_client(session_id, req.model)
            lock = _session_locks[session_id]
            async with lock:
                preface = _attached_files_preface(session_id)
                await client.query(preface + _apply_mode(req.message, req.mode))
                async for message in client.receive_response():
                    for event in _events_from_message(message):
                        yield _sse(event)
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
        yield _sse({"type": "done"})

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/interrupt")
async def interrupt(req: ChatRequest):
    """Best-effort cancellation of the session's in-flight query.

    Requires the installed Claude Agent SDK to expose `interrupt()`. If it
    doesn't, we return 501 so the UI can fall back gracefully.
    """
    sid = req.session_id
    if not sid or sid not in _sessions:
        raise HTTPException(404, "No active session")
    client = _sessions[sid]
    interrupt_fn = getattr(client, "interrupt", None)
    if interrupt_fn is None:
        raise HTTPException(501, "Interrupt not supported by the installed Claude Agent SDK")
    try:
        result = interrupt_fn()
        if asyncio.iscoroutine(result):
            await result
    except Exception as exc:  # pragma: no cover - surface SDK failure to UI
        raise HTTPException(500, f"Interrupt failed: {exc}")
    return {"ok": True}


@app.post("/api/reset")
async def reset(req: ChatRequest):
    sid = req.session_id
    if sid:
        await _drop_session(sid)
        safe = _sanitize_session_id(sid)
        shutil.rmtree(UPLOADS_DIR / safe, ignore_errors=True)
    return {"ok": True}


def _mask_api_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 14:
        return key[:4] + "…"
    return f"{key[:10]}…{key[-4:]}"


@app.get("/api/config")
async def get_config():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    return {
        "models": AVAILABLE_MODELS,
        "default_model": _resolve_model(None),
        "has_api_key": bool(api_key),
        "api_key_preview": _mask_api_key(api_key),
    }


class ApiKeyRequest(BaseModel):
    api_key: str


@app.post("/api/api-key")
async def set_api_key(req: ApiKeyRequest):
    """Store an API key in the backend process memory only.

    We don't persist it to disk. Restarting the backend forgets it and the
    user will be prompted again (or the env var from .env takes over).
    """
    key = (req.api_key or "").strip()
    if not key.startswith("sk-"):
        raise HTTPException(400, "Invalid API key format (expected to start with 'sk-').")
    os.environ["ANTHROPIC_API_KEY"] = key
    # Any clients created before this point won't pick up the new key, so
    # drop them — they'll be recreated transparently on the next /api/chat.
    for sid in list(_sessions.keys()):
        await _drop_session(sid)
    return {"ok": True}


@app.post("/api/upload")
async def upload(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    d = _session_upload_dir(session_id)
    existing = [p for p in d.iterdir() if p.is_file()]
    if len(existing) >= MAX_SESSION_UPLOAD_FILES:
        raise HTTPException(
            413,
            f"Too many attached files; max {MAX_SESSION_UPLOAD_FILES} per session.",
        )
    name = _safe_filename(file.filename or "file")
    target = d / name
    total = 0
    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(
                        413,
                        f"File too large; max {MAX_UPLOAD_BYTES // (1024*1024)} MB per file.",
                    )
                out.write(chunk)
    finally:
        await file.close()
    return {"ok": True, "files": _list_session_uploads(session_id)}


@app.get("/api/uploads/{session_id}")
async def list_uploads(session_id: str):
    return {"files": _list_session_uploads(session_id)}


@app.delete("/api/uploads/{session_id}/{filename}")
async def delete_upload(session_id: str, filename: str):
    d = _session_upload_dir(session_id, create=False)
    safe = _safe_filename(filename)
    target = (d / safe).resolve()
    # Defense-in-depth: make sure we're deleting inside the session dir.
    if d.is_dir() and target.is_file() and target.is_relative_to(d.resolve()):
        target.unlink()
    return {"files": _list_session_uploads(session_id)}


if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )

    @app.get("/")
    async def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn

    _ensure_repos()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8001")),
        reload=False,
    )
