"""
Chat assistant endpoints for Memgraph Assistant.
Uses OpenAI Agents SDK with reasoning capabilities to understand documentation and perform graph operations.
"""
import os
import logging
import sys
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
from .models import ChatRequest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# MCP service URLs
MCP_URL = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")  # Documentation graph
MCP_MAIN_URL = os.getenv("MCP_MEMGRAPH_MAIN_URL", "http://localhost:8002/mcp")  # Main graph

# Model configuration
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o")

from agents import Agent, Runner
from agents.model_settings import ModelSettings
from agents.mcp import MCPServerStreamableHttp
from agents.mcp.util import create_static_tool_filter
from agents.memory import SQLiteSession, Session
from .prompts import (
    get_main_graph_agent_instructions,
    get_documentation_agent_instructions,
)
from .common import extract_structured_content
from .custom_tools import (
    create_vector_search_tool,
    create_keyword_search_tool,
    create_relevance_expansion_tool,
)
from .mcp_interceptor import create_interceptor

# Session storage
_sessions: dict[str, Session] = {}

# Store intercepting servers per session for approval workflow
# Each session has two interceptors: one for documentation, one for main graph
_session_interceptors: dict[str, dict[str, Any]] = {}  # {session_id: {"docs": interceptor, "main": interceptor}}

# Directory for session database files
SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "sessions"))
SESSIONS_DIR.mkdir(exist_ok=True)


def get_or_create_session(session_id: str | None) -> Session:
    """Get existing session or create a new one with persistent storage."""
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    if session_id not in _sessions:
        db_path = SESSIONS_DIR / "conversations.db"
        _sessions[session_id] = SQLiteSession(
            session_id=session_id,
            db_path=str(db_path)
        )
        logger.info(f"Created new persistent session: {session_id}")
    else:
        logger.debug(f"Reusing existing session: {session_id}")
    
    return _sessions[session_id]


def create_documentation_agent(model: str, server) -> Agent:
    """Create the documentation agent that searches and understands documentation."""
    vector_search_tool = create_vector_search_tool(mcp_server=server)
    keyword_search_tool = create_keyword_search_tool(mcp_server=server)
    relevance_expansion_tool = create_relevance_expansion_tool(mcp_server=server)
    
    return Agent(
        name="Documentation Agent",
        instructions=get_documentation_agent_instructions(),
        model=model,
        mcp_servers=[server],
        tools=[vector_search_tool, keyword_search_tool, relevance_expansion_tool],
        model_settings=ModelSettings(
            tool_choice="required",
            temperature=0.1,
            parallel_tool_calls=False,
        ),
    )


def create_main_graph_agent(model: str, main_server, docs_server=None, mode: str = "agent") -> Agent:
    """
    Create the main graph agent that executes queries and operations on the main graph.
    
    Args:
        model: The model to use
        main_server: MCP server for the main graph
        docs_server: Optional MCP server for documentation (allows agent to query docs for help)
        mode: "agent" or "ask" - determines behavior for write operations
    """
    tools = []
    mcp_servers = [main_server]
    
    # If documentation server is provided, add documentation tools
    # Note: We don't add docs_server to mcp_servers to avoid duplicate tool names (run_query, get_schema)
    # Instead, we use custom tools that wrap the docs_server functionality
    if docs_server:
        tools.extend([
            create_vector_search_tool(mcp_server=docs_server),
            create_keyword_search_tool(mcp_server=docs_server),
            create_relevance_expansion_tool(mcp_server=docs_server),
        ])
        # Don't add docs_server to mcp_servers - it would cause duplicate tool names
    
    return Agent(
        name="Main Graph Agent",
        instructions=get_main_graph_agent_instructions(),
        model=model,
        mcp_servers=mcp_servers,
        tools=tools,
        model_settings=ModelSettings(
            tool_choice="required",
            temperature=0.1,
            parallel_tool_calls=False,
        ),
    )


def create_manager_agent(docs_agent: Agent, main_graph_agent: Agent, model: str, mode: str = "agent") -> Agent:
    """Create the manager agent that orchestrates the chat and routes between agents."""
    from .prompts import get_manager_agent_instructions
    return Agent(
        name="Memgraph Assistant",
        instructions=get_manager_agent_instructions(mode),
        model=model,
        tools=[
            docs_agent.as_tool(
                tool_name="documentation_agent",
                tool_description="Searches and understands Memgraph documentation. Use this when the user asks questions about Memgraph features, syntax, how to use something, or needs documentation information.",
            ),
            main_graph_agent.as_tool(
                tool_name="main_graph_agent",
                tool_description="Executes queries and operations on the main graph database (port 7688). Use this when the user wants to query or modify their actual data graph. Write operations will require approval.",
            ),
        ],
        model_settings=ModelSettings(
            tool_choice="auto",
            temperature=0.3,
        ),
    )




def create_mcp_server_context(
    mcp_url: str,
    timeout: float = 60.0,
    allowed_tool_names: list[str] | None = None,
    server_name: str = "Memgraph MCP Server"
) -> MCPServerStreamableHttp:
    """
    Create an MCPServerStreamableHttp context manager with the specified configuration.
    
    Args:
        mcp_url: URL of the MCP server (e.g., "http://localhost:8001/mcp")
        timeout: Timeout for MCP server connections
        allowed_tool_names: List of allowed tool names (default: ["run_query", "get_schema"])
        server_name: Name for the MCP server
    
    Returns:
        MCPServerStreamableHttp instance to be used as async context manager
    """
    if allowed_tool_names is None:
        allowed_tool_names = ["run_query", "get_schema"]
    
    return MCPServerStreamableHttp(
        name=server_name,
        params={
            "url": mcp_url,
            "headers": {},
            "timeout": timeout,
        },
        cache_tools_list=True,
        tool_filter=create_static_tool_filter(
            allowed_tool_names=allowed_tool_names
        ),
        client_session_timeout_seconds=timeout,
    )


@router.post("/query-stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with the Memgraph Assistant with streaming updates via Server-Sent Events (SSE).
    """
    if not request.question or not isinstance(request.question, str):
        raise HTTPException(
            status_code=400,
            detail="No question provided. Please provide a 'question' string.",
        )

    async def event_generator():
        """Generator function for SSE events."""
        try:
            session = get_or_create_session(request.session_id)
            
            # Create documentation MCP server and interceptor
            async with create_mcp_server_context(
                mcp_url=MCP_URL,
                timeout=60.0,
                server_name="Memgraph Documentation MCP Server"
            ) as docs_base_server:
                docs_interceptor = create_interceptor(
                    base_server=docs_base_server,
                    name="Documentation Graph"
                )
                
                logger.info(
                    f"🔧 Created Documentation InterceptingMCPServer for session {session.session_id}\n"
                    f"  - MCP URL: {MCP_URL} (documentation graph)\n"
                    f"  - Mode: {request.mode}"
                )
                
                # Create main graph MCP server and interceptor
                async with create_mcp_server_context(
                    mcp_url=MCP_MAIN_URL,
                    timeout=60.0,
                    server_name="Memgraph Main Graph MCP Server"
                ) as main_base_server:
                    main_interceptor = create_interceptor(
                        base_server=main_base_server,
                        name="Main Graph"
                    )
                    
                    logger.info(
                        f"🔧 Created Main Graph InterceptingMCPServer for session {session.session_id}\n"
                        f"  - Mode: {request.mode}\n"
                        f"  - MCP URL: {MCP_MAIN_URL} (main graph)"
                    )
                    
                    # Store both interceptors for this session
                    _session_interceptors[session.session_id] = {
                        "docs": docs_interceptor,
                        "main": main_interceptor
                    }
                    
                    # Create both agents with mode context
                    # Main graph agent gets access to documentation tools for help
                    docs_agent = create_documentation_agent(CHAT_MODEL, docs_interceptor)
                    main_graph_agent = create_main_graph_agent(CHAT_MODEL, main_interceptor, docs_interceptor, request.mode)
                    manager_agent = create_manager_agent(docs_agent, main_graph_agent, CHAT_MODEL, request.mode)

                    logger.info(f"Running chat assistant with session {session.session_id}...")
                    
                    result = await Runner.run(
                        manager_agent, 
                        request.question,
                        session=session
                    )
                    
                    logger.info(f"Agent run completed. Final output: {result.final_output[:100] if result.final_output else 'None'}...")
                    
                    # Get queries from both interceptors
                    docs_run_query_calls = docs_interceptor.get_run_query_calls()
                    main_run_query_calls = main_interceptor.get_run_query_calls()
                    all_run_query_calls = [
                        {**call, "source": "documentation"} for call in docs_run_query_calls
                    ] + [
                        {**call, "source": "main_graph"} for call in main_run_query_calls
                    ]
                    
                    logger.info(
                        f"📊 INTERCEPTOR: Final statistics\n"
                        f"  - Documentation run_query calls: {len(docs_run_query_calls)}\n"
                        f"  - Main graph run_query calls: {len(main_run_query_calls)}\n"
                        f"  - Total run_query calls: {len(all_run_query_calls)}"
                    )
                    
                    answer = result.final_output or "I apologize, but I couldn't generate a response. Please try rephrasing your question."
                    
                    final_result = {
                        "question": request.question,
                        "answer": answer,
                        "status": "success",
                        "session_id": session.session_id,
                        "agent_run_id": getattr(result, "run_id", None),
                        "run_query_calls": all_run_query_calls,
                    }
                    
                    logger.info(f"Final result prepared. Answer length: {len(answer)}")
                    yield f"data: {json.dumps({'type': 'result', 'data': final_result})}\n\n"
        
        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}", exc_info=True)
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


@router.post("/query")
async def chat(request: ChatRequest):
    """
    Chat with the Memgraph Assistant.
    Understands documentation and can perform graph operations.
    """
    if not request.question or not isinstance(request.question, str):
        raise HTTPException(
            status_code=400,
            detail="No question provided. Please provide a 'question' string.",
        )

    try:
        session = get_or_create_session(request.session_id)
        
        # Create documentation MCP server and interceptor
        async with create_mcp_server_context(
            mcp_url=MCP_URL,
            timeout=60.0,
            server_name="Memgraph Documentation MCP Server"
        ) as docs_base_server:
            docs_interceptor = create_interceptor(
                base_server=docs_base_server,
                name="Documentation Graph"
            )
            
            # Create main graph MCP server and interceptor
            async with create_mcp_server_context(
                mcp_url=MCP_MAIN_URL,
                timeout=60.0,
                server_name="Memgraph Main Graph MCP Server"
            ) as main_base_server:
                main_interceptor = create_interceptor(
                    base_server=main_base_server,
                    name="Main Graph"
                )
                
                # Store both interceptors for this session
                _session_interceptors[session.session_id] = {
                    "docs": docs_interceptor,
                    "main": main_interceptor
                }
                
                # Create both agents with mode context
                # Main graph agent gets access to documentation tools for help
                docs_agent = create_documentation_agent(CHAT_MODEL, docs_interceptor)
                main_graph_agent = create_main_graph_agent(CHAT_MODEL, main_interceptor, docs_interceptor, request.mode)
                manager_agent = create_manager_agent(docs_agent, main_graph_agent, CHAT_MODEL, request.mode)

                logger.info(f"Running chat assistant with session {session.session_id}...")

                result = await Runner.run(
                    manager_agent, 
                    request.question,
                    session=session
                )
                
                # Get queries from both interceptors
                docs_run_query_calls = docs_interceptor.get_run_query_calls()
                main_run_query_calls = main_interceptor.get_run_query_calls()
                all_run_query_calls = [
                    {**call, "source": "documentation"} for call in docs_run_query_calls
                ] + [
                    {**call, "source": "main_graph"} for call in main_run_query_calls
                ]

                return {
                    "question": request.question,
                    "answer": result.final_output,
                    "status": "success",
                    "session_id": session.session_id,
                    "agent_run_id": getattr(result, "run_id", None),
                    "run_query_calls": all_run_query_calls,
                }

    except Exception as e:
        logger.error(f"Error running chat assistant: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error running chat assistant: {str(e)}"
        )



