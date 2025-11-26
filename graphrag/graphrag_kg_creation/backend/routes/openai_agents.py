"""
OpenAI Agents SDK integration with MCP servers.
Uses Streamable HTTP transport for MCP communication.
"""
import os
import logging
import sys
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openai-agents", tags=["openai-agents"])

# MCP service URL - use service name when running in Docker, localhost when running locally
# Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
MCP_URL = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")

from agents import Agent, Runner
from agents.model_settings import ModelSettings
from agents.mcp import MCPServerStreamableHttp


class QueryRequest(BaseModel):
    """Request model for agent queries."""
    question: str
    instructions: Optional[str] = None
    tool_choice: Optional[str] = None  # "auto", "required", "none", or tool name
    model: Optional[str] = None  # Override default model
    temperature: Optional[float] = None  # Override default temperature


@router.post("/query")
async def query_with_agent(request: QueryRequest):
    """
    Query the knowledge graph using OpenAI Agents SDK with MCP server.
    
    The agent uses the MCP server tools to answer questions about the knowledge graph.
    This leverages the OpenAI Agents SDK which handles tool selection and execution automatically.
    
    Expected JSON body:
    {
        "question": "What is Memgraph?",
        "instructions": "Optional custom instructions for the agent",
        "tool_choice": "required",  // Optional: "auto", "required", "none", or tool name
        "model": "gpt-4o",  // Optional: override default model
        "temperature": 0.1  // Optional: override default temperature
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
        async with MCPServerStreamableHttp(
            name="Memgraph MCP Server",
            params={
                "url": MCP_URL,
                "headers": {},  # Add any required headers here
            },
            cache_tools_list=True,  # Cache tools list to reduce latency
        ) as server:
            # Configure agent
            agent_config = {
                "name": "Knowledge Graph Assistant",
                "instructions": request.instructions or "You are a helpful assistant that answers questions about the knowledge graph using the available MCP tools.",
                "mcp_servers": [server],
            }
            
            # Add model settings if tool_choice is specified
            if request.tool_choice:
                agent_config["model_settings"] = ModelSettings(tool_choice=request.tool_choice)
            
            # Create agent
            agent = Agent(**agent_config)
            
            # Run the agent with the question
            result = await Runner.run(agent, request.question)
            
            return {
                "question": request.question,
                "answer": result.final_output,
                "status": "success",
                "agent_run_id": getattr(result, "run_id", None),
            }
        
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error running agent: {str(e)}"
        )

