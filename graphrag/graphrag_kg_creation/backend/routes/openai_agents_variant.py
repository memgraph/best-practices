"""
OpenAI Agents SDK integration with MCP servers - Variant with custom tool.
This variant is the same as openai_agents.py but includes an additional custom tool.
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

router = APIRouter(prefix="/openai-agents-variant", tags=["openai-agents-variant"])

# MCP service URL - use service name when running in Docker, localhost when running locally
# Default to localhost:8001 for local development (host port), or set MCP_MEMGRAPH_URL env var
MCP_URL = os.getenv("MCP_MEMGRAPH_URL", "http://localhost:8001/mcp")

# Model configuration - defaults to gpt-4o (supports temperature)
# Set OPENAI_AGENTS_VARIANT_MODEL env var to override
VARIANT_MODEL = os.getenv("OPENAI_AGENTS_VARIANT_MODEL", "gpt-4o")

from agents import Agent, Runner
from agents.model_settings import ModelSettings
from agents.mcp import MCPServerStreamableHttp
from agents.mcp.util import create_static_tool_filter
from agents.tool import function_tool
from agents.items import ToolCallItem, MessageOutputItem, ToolCallOutputItem, ReasoningItem
from agents.items import ItemHelpers
from .prompts import DEFAULT_AGENT_INSTRUCTIONS


# Custom tool: say_hey_custom_tool
@function_tool
def say_hey_custom_tool() -> str:
    """Say hey! A simple greeting tool."""
    return "hey"


class QueryRequest(BaseModel):
    """Request model for variant agent queries."""
    question: str


def extract_tools_used(result) -> list[dict]:
    """
    Extract tool calls from the agent run result.
    
    Args:
        result: The RunResult object from Runner.run()
        
    Returns:
        A list of dictionaries containing tool name and arguments for each tool call.
    """
    tools_used = []
    for item in result.new_items:
        if isinstance(item, ToolCallItem):
            # Extract tool name from raw_item
            raw_item = item.raw_item
            tool_name = None
            tool_arguments = None
            
            # Handle different raw_item formats
            if isinstance(raw_item, dict):
                # Check for function tool call format
                if "function" in raw_item:
                    tool_name = raw_item["function"].get("name")
                    tool_arguments = raw_item["function"].get("arguments")
                # Check for direct name field (MCP calls)
                elif "name" in raw_item:
                    tool_name = raw_item["name"]
                    tool_arguments = raw_item.get("arguments")
            elif hasattr(raw_item, "function"):
                # Handle object with function attribute
                tool_name = getattr(raw_item.function, "name", None)
                tool_arguments = getattr(raw_item.function, "arguments", None)
            elif hasattr(raw_item, "name"):
                # Handle object with name attribute
                tool_name = getattr(raw_item, "name", None)
                tool_arguments = getattr(raw_item, "arguments", None)
            
            if tool_name:
                tools_used.append({
                    "name": tool_name,
                    "arguments": tool_arguments,
                })
    
    return tools_used


def extract_conversation_history(result, user_question: str) -> list[dict]:
    """
    Extract the conversation history between the agent and LLM.
    
    Args:
        result: The RunResult object from Runner.run()
        user_question: The original user question
        
    Returns:
        A list of dictionaries representing the conversation history.
    """
    conversation = []
    
    # Add user question as first message
    conversation.append({
        "role": "user",
        "type": "message",
        "content": user_question,
    })
    
    # Process all items in order
    for item in result.new_items:
        if isinstance(item, MessageOutputItem):
            # Extract message content
            message_text = ItemHelpers.text_message_output(item)
            conversation.append({
                "role": "assistant",
                "type": "message",
                "content": message_text,
            })
        
        elif isinstance(item, ToolCallItem):
            # Extract tool call information
            raw_item = item.raw_item
            tool_name = None
            tool_arguments = None
            
            if isinstance(raw_item, dict):
                if "function" in raw_item:
                    tool_name = raw_item["function"].get("name")
                    tool_arguments = raw_item["function"].get("arguments")
                elif "name" in raw_item:
                    tool_name = raw_item["name"]
                    tool_arguments = raw_item.get("arguments")
            elif hasattr(raw_item, "function"):
                tool_name = getattr(raw_item.function, "name", None)
                tool_arguments = getattr(raw_item.function, "arguments", None)
            elif hasattr(raw_item, "name"):
                tool_name = getattr(raw_item, "name", None)
                tool_arguments = getattr(raw_item, "arguments", None)
            
            if tool_name:
                conversation.append({
                    "role": "assistant",
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "arguments": tool_arguments,
                })
        
        elif isinstance(item, ToolCallOutputItem):
            # Extract tool output
            output = item.output
            # Convert output to string if needed
            if isinstance(output, str):
                output_str = output
            else:
                try:
                    output_str = json.dumps(output, indent=2)
                except:
                    output_str = str(output)
            
            conversation.append({
                "role": "tool",
                "type": "tool_output",
                "content": output_str,
            })
        
        elif isinstance(item, ReasoningItem):
            # Extract reasoning content
            raw_item = item.raw_item
            reasoning_text = None
            
            if isinstance(raw_item, dict):
                reasoning_text = raw_item.get("content") or raw_item.get("text")
            elif hasattr(raw_item, "content"):
                reasoning_text = getattr(raw_item, "content", None)
            elif hasattr(raw_item, "text"):
                reasoning_text = getattr(raw_item, "text", None)
            
            if reasoning_text:
                conversation.append({
                    "role": "assistant",
                    "type": "reasoning",
                    "content": reasoning_text,
                })
    
    return conversation


@router.post("/query")
async def query_with_agent_variant(request: QueryRequest):
    """
    Query the knowledge graph using OpenAI Agents SDK with MCP server - Variant with custom tool.
    
    This variant is the same as openai_agents.py but includes an additional custom "say_hey" tool.
    The agent can use this tool along with the MCP tools (run_query, get_schema).
    
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
        # Filter tools to only allow run_query and get_schema (same as openai_agents.py)
        
        async with MCPServerStreamableHttp(
            name="Memgraph MCP Server",
            params={
                "url": MCP_URL,
                "headers": {},  # Add any required headers here
            },
            cache_tools_list=True,  # Cache tools list to reduce latency
            tool_filter=create_static_tool_filter(allowed_tool_names=["run_query", "get_schema"]),
        ) as server:
            # Configure agent - same settings as openai_agents.py
            # But includes the custom say_hey tool
            agent_config = {
                "name": "Knowledge Graph Assistant (Variant)",
                "instructions": DEFAULT_AGENT_INSTRUCTIONS,
                "model": VARIANT_MODEL,  # Defaults to gpt-4o
                "mcp_servers": [server],
                "tools": [say_hey_custom_tool],  # Add custom tool here
                "model_settings": ModelSettings(
                    tool_choice="required",  # Always require tools (same as openai_agents.py)
                    temperature=0.1,  # Low temperature for deterministic responses (same as openai_agents.py)
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
        logger.error(f"Error running variant agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error running variant agent: {str(e)}"
        )

