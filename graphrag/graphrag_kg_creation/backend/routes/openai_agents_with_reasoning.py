"""
OpenAI Agents SDK integration with MCP servers - Multi-Agent Orchestration with Planning and Reasoning.
This variant implements a Manager (agents as tools) pattern with explicit reasoning:
- Manager agent: Orchestrates the planning, execution, and reasoning process
- Planner agent: Exposed as a tool, generates 5-10 high-level query strategies
- Execution agent: Exposed as a tool, executes strategies using MCP tools with chain-of-thought reasoning
- Reasoning agent: Exposed as a tool, analyzes execution results and guides next steps

Reference: https://openai.github.io/openai-agents-python/agents/#multi-agent-system-design-patterns
"""

import os
import logging
import sys
import json
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/openai-agents-with-reasoning", tags=["openai-agents-with-reasoning"]
)

# MCP service URL - use service name when running in Docker, localhost when running locally
# Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
MCP_URL = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")

# Model configuration - defaults to gpt-4o (supports temperature)
# Set OPENAI_AGENTS_WITH_REASONING_MODEL env var to override
# For reasoning agent, you can use o1-preview or o1-mini for enhanced reasoning capabilities
REASONING_MODEL = os.getenv("OPENAI_AGENTS_WITH_REASONING_MODEL", "gpt-4o")
REASONING_AGENT_MODEL = os.getenv("REASONING_AGENT_MODEL", "gpt-4o")  # Can be set to "o1-preview" or "o1-mini"

from agents import Agent, Runner
from agents.model_settings import ModelSettings
from agents.mcp import MCPServerStreamableHttp
from agents.mcp.util import create_static_tool_filter
from agents.memory import SQLiteSession, Session
from .prompts import (
    PLANNER_AGENT_INSTRUCTIONS,
    EXECUTION_AGENT_WITH_REASONING_INSTRUCTIONS,
    MANAGER_AGENT_WITH_REASONING_INSTRUCTIONS,
    REASONING_AGENT_INSTRUCTIONS,
)
from .common import extract_tools_used, build_trace_graph_from_items
from .custom_tools import create_vector_search_tool
from .mcp_interceptor import InterceptingMCPServer

# Session storage - dictionary mapping session_id to Session objects
_sessions: dict[str, Session] = {}

# Directory for session database files
SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "sessions"))
SESSIONS_DIR.mkdir(exist_ok=True)  # Create directory if it doesn't exist


def get_or_create_session(session_id: str | None) -> Session:
    """
    Get existing session or create a new one with persistent storage.
    
    According to the OpenAI Agents SDK documentation:
    - Use file-based SQLite for persistent conversations
    - Use in-memory SQLite for temporary conversations
    
    Args:
        session_id: Optional session ID. If None, creates a new session.
        
    Returns:
        Session object with the given or newly generated session_id
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    if session_id not in _sessions:
        # Use a single shared database file for all sessions
        # The SQLiteSession implementation handles session isolation internally
        db_path = SESSIONS_DIR / "conversations.db"
        
        _sessions[session_id] = SQLiteSession(
            session_id=session_id,
            db_path=str(db_path)
        )
        logger.info(f"Created new persistent session: {session_id} (db: {db_path})")
    else:
        logger.debug(f"Reusing existing session: {session_id}")
    
    return _sessions[session_id]


class QueryRequest(BaseModel):
    """Request model for reasoning agent queries."""

    question: str
    session_id: str | None = None  # Optional session ID for conversation continuity


def parse_strategies_from_planner_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Parse strategies from planner agent response.
    Attempts to extract JSON array from the response.

    Args:
        response_text: The planner agent's response text

    Returns:
        List of strategy dictionaries
    """
    strategies = []

    try:
        # Try to find JSON array in the response
        json_match = re.search(r"\[[\s\S]*\]", response_text)
        if json_match:
            strategies_data = json.loads(json_match.group())
            if isinstance(strategies_data, list):
                strategies = strategies_data
        # Try to find JSON object with "strategies" key
        elif re.search(r"\{", response_text):
            json_obj_match = re.search(r"\{[\s\S]*\}", response_text, re.DOTALL)
            if json_obj_match:
                strategies_data = json.loads(json_obj_match.group())
                if (
                    isinstance(strategies_data, dict)
                    and "strategies" in strategies_data
                ):
                    strategies = strategies_data["strategies"]
                elif isinstance(strategies_data, list):
                    strategies = strategies_data
    except json.JSONDecodeError as e:
        logger.warning(f"Could not parse JSON from planner response: {str(e)}")
        logger.debug(f"Response text: {response_text[:500]}")
    except Exception as e:
        logger.warning(f"Error parsing planner strategies: {str(e)}")

    return strategies


def create_planner_agent(model: str) -> Agent:
    """
    Create the planner agent that generates query strategies.

    Args:
        model: The model to use for the planner

    Returns:
        Configured planner agent
    """
    return Agent(
        name="Query Planner",
        instructions=PLANNER_AGENT_INSTRUCTIONS,
        model=model,
        model_settings=ModelSettings(
            tool_choice="none",  # Planner doesn't need tools, just generates strategies
            temperature=0.7,  # Higher temperature for more creative/diverse strategies
        ),
    )


def create_execution_agent(model: str, server) -> Agent:
    """
    Create the execution agent that executes query strategies with chain-of-thought reasoning.

    Args:
        model: The model to use for execution
        server: The MCP server instance (should be InterceptingMCPServer)

    Returns:
        Configured execution agent
    """
    # Create vector_search tool that uses the intercepting MCP server
    # This way all queries go through the same interceptor
    vector_search_tool = create_vector_search_tool(mcp_server=server)
    
    return Agent(
        name="Query Executor",
        instructions=EXECUTION_AGENT_WITH_REASONING_INSTRUCTIONS,
        model=model,
        mcp_servers=[server],  # Provides MCP tools: get_schema, run_query
        tools=[vector_search_tool],  # Custom tool for vector search (uses MCP server, goes through interceptor)
        model_settings=ModelSettings(
            tool_choice="required",
            temperature=0.1,
            parallel_tool_calls=False,
        ),
    )


def create_reasoning_agent(model: str) -> Agent:
    """
    Create the reasoning agent that analyzes execution results.

    Args:
        model: The model to use for reasoning (can be o1-preview or o1-mini for enhanced reasoning)

    Returns:
        Configured reasoning agent
    """
    # Check if using o1 model (doesn't support temperature)
    model_settings = {}
    if model.startswith("o1"):
        # o1 models don't support temperature parameter
        model_settings = ModelSettings(
            tool_choice="none",  # Pure reasoning, no tools needed
        )
    else:
        model_settings = ModelSettings(
            tool_choice="none",  # Pure reasoning, no tools needed
            temperature=0.3,  # Balanced for analytical thinking
        )
    
    return Agent(
        name="Query Reasoner",
        instructions=REASONING_AGENT_INSTRUCTIONS,
        model=model,
        model_settings=model_settings,
    )


def create_manager_agent(
    planner_agent: Agent, 
    execution_agent: Agent, 
    reasoning_agent: Agent,
    model: str
) -> Agent:
    """
    Create the manager agent that orchestrates planning, execution, and reasoning.
    Uses the Manager (agents as tools) pattern from OpenAI Agents SDK.

    Args:
        planner_agent: The planner agent to expose as a tool
        execution_agent: The execution agent to expose as a tool
        reasoning_agent: The reasoning agent to expose as a tool
        model: The model to use for the manager

    Returns:
        Configured manager agent
    """
    return Agent(
        name="Query Manager",
        instructions=MANAGER_AGENT_WITH_REASONING_INSTRUCTIONS,
        model=model,
        tools=[
            planner_agent.as_tool(
                tool_name="query_planner",
                tool_description="Generates 5-10 high-level strategies for querying the Memgraph knowledge graph to answer a question. Call this first to get query strategies.",
            ),
            execution_agent.as_tool(
                tool_name="query_executor",
                tool_description="Executes a specific query strategy using available tools: MCP tools (get_schema, run_query) and custom tools (vector_search_on_chunks). Provides explicit reasoning about the execution process.",
            ),
            reasoning_agent.as_tool(
                tool_name="query_reasoner",
                tool_description="Analyzes results from executed strategies, identifies gaps, synthesizes information, and recommends next steps. Call this after executing strategies to get reasoning insights and determine if more execution is needed.",
            ),
        ],
        model_settings=ModelSettings(
            tool_choice="auto",  # Manager decides when to use tools
            temperature=0.3,  # Moderate temperature for balanced decision-making
        ),
    )


@router.post("/query")
async def query_with_reasoning(request: QueryRequest):
    """
    Query the knowledge graph using multi-agent orchestration with planning and reasoning.

    This variant implements the Manager (agents as tools) pattern with explicit reasoning:
    - Manager agent orchestrates the process and retains control of the conversation
    - Planner agent is exposed as a tool that generates query strategies
    - Execution agent is exposed as a tool that executes strategies with chain-of-thought reasoning
    - Reasoning agent is exposed as a tool that analyzes results and guides next steps

    Expected JSON body:
    {
        "question": "What is Memgraph?",
        "session_id": "optional-session-id-for-conversation-continuity"
    }
    """
    if not request.question or not isinstance(request.question, str):
        raise HTTPException(
            status_code=400,
            detail="No question provided. Please provide a 'question' string.",
        )

    try:
        # Get or create session for conversation continuity
        session = get_or_create_session(request.session_id)
        
        # Set up MCP server connection
        async with MCPServerStreamableHttp(
            name="Memgraph MCP Server",
            params={
                "url": MCP_URL,
                "headers": {},
                "timeout": 60.0,  # Increase timeout to 60 seconds for get_schema and run_query calls
            },
            cache_tools_list=True,
            tool_filter=create_static_tool_filter(
                allowed_tool_names=["run_query", "get_schema"]
            ),
            client_session_timeout_seconds=60.0,
        ) as base_server:
            # Wrap the server to intercept run_query calls
            # The base_server is already connected via the async context manager
            intercepting_server = InterceptingMCPServer(base_server)
            
            # Create specialized sub-agents with the intercepting server
            planner_agent = create_planner_agent(REASONING_MODEL)
            execution_agent = create_execution_agent(REASONING_MODEL, intercepting_server)
            reasoning_agent = create_reasoning_agent(REASONING_AGENT_MODEL)

            # Create manager agent that orchestrates the sub-agents as tools
            manager_agent = create_manager_agent(
                planner_agent, execution_agent, reasoning_agent, REASONING_MODEL
            )

            logger.info(f"Running manager agent with reasoning with session {session.session_id}...")

            # Run the manager agent with session - this maintains conversation history
            result = await Runner.run(
                manager_agent, 
                request.question,
                session=session  # Pass session here for conversation continuity
            )

            # Build trace graph from result.new_items
            trace_data = build_trace_graph_from_items(result, request.question)

            # Extract information from the manager's run
            # Include nested tools from agent-as-tool invocations (e.g., query_executor -> get_schema, run_query)
            tools_used = extract_tools_used(result, include_nested=True)
            
            # Get intercepted run_query calls (includes both MCP run_query and vector_search queries)
            run_query_calls = intercepting_server.get_run_query_calls()

            return {
                "question": request.question,
                "answer": result.final_output,
                "status": "success",
                "session_id": session.session_id,  # Return session_id so frontend can reuse it
                "agent_run_id": getattr(result, "run_id", None),
                "tools_used": tools_used,
                "run_query_calls": run_query_calls,  # All intercepted run_query calls
                "tool_call_graph": trace_data,  # Use trace data instead of tool call graph
            }

    except Exception as e:
        logger.error(f"Error running reasoning agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error running reasoning agent: {str(e)}"
        )

