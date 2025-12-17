"""
OpenAI Agents SDK integration with MCP servers.
Uses Streamable HTTP transport for MCP communication.
"""
import os
import logging
import sys
import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openai-agents", tags=["openai-agents"])

# MCP service URL - use service name when running in Docker, localhost when running locally
# Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
MCP_URL = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")

# Model configuration - defaults to gpt-4o (supports temperature)
# Set OPENAI_AGENTS_MODEL env var to override (e.g., "gpt-4o", "gpt-4o-mini", "o1", etc.)
# Note: GPT-5 and o1 models don't support temperature parameter
AGENT_MODEL = os.getenv("OPENAI_AGENTS_MODEL", "gpt-4o")

from agents import Agent, Runner
from agents.model_settings import ModelSettings
from agents.mcp import MCPServerStreamableHttp
from agents.mcp.util import create_static_tool_filter
from .prompts import DEFAULT_AGENT_INSTRUCTIONS
from .common import extract_tools_used, extract_conversation_history


class QueryRequest(BaseModel):
    """Request model for agent queries."""
    question: str


@router.post("/query")
async def query_with_agent(request: QueryRequest):
    """
    Query the knowledge graph using OpenAI Agents SDK with MCP server.
    
    The agent uses the MCP server tools to answer questions about the knowledge graph.
    This leverages the OpenAI Agents SDK which handles tool selection and execution automatically.
    
    Expected JSON body:
    {
        "question": "What is Memgraph?"
    }
    """
    if not request.question or not isinstance(request.question, str):
        raise HTTPException(
            status_code=400,
            detail="No question provided. Please provide a 'question' string."
        )
    
    try:
        # Configure MCP server connection using Streamable HTTP transport
        # The MCP server uses streamable-http transport on the /mcp endpoint
        
        # Create MCP server instance with Streamable HTTP transport and use as async context manager
        # Filter tools to only allow run_query and get_schema
        async with MCPServerStreamableHttp(
            name="Memgraph MCP Server",
            params={
                "url": MCP_URL,
                "headers": {},  # Add any required headers here
                "timeout": 60.0,  # Increase timeout to 60 seconds for get_schema and run_query calls
            },
            cache_tools_list=True,  # Cache tools list to reduce latency
            tool_filter=create_static_tool_filter(allowed_tool_names=["run_query", "get_schema"]),
        ) as server:
            # Configure agent - defaults to gpt-4o (supports temperature)
            # Model can be set via OPENAI_AGENTS_MODEL env var
            # Note: GPT-5 and o1 models don't support temperature parameter
            agent_config = {
                "name": "Knowledge Graph Assistant",
                "instructions": DEFAULT_AGENT_INSTRUCTIONS,
                "model": AGENT_MODEL,  # Defaults to gpt-4o
                "mcp_servers": [server],
                "model_settings": ModelSettings(
                    tool_choice="required",  # Always require tools
                    temperature=0.1,  # Low temperature for deterministic responses (supported by gpt-4o)
                ),
            }
            
            # Create agent
            agent = Agent(**agent_config)
            
            # Run the agent with the question
            result = await Runner.run(agent, request.question)
            
            # Extract tool calls from the result
            tools_used = extract_tools_used(result)
            
            # Extract conversation history
            conversation_history = extract_conversation_history(result, request.question)
            
            return {
                "question": request.question,
                "answer": result.final_output,
                "status": "success",
                "agent_run_id": getattr(result, "run_id", None),
                "tools_used": tools_used,
                "conversation_history": conversation_history,
            }
        
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error running agent: {str(e)}"
        )
