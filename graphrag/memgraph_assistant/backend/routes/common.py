"""
Common utility functions for OpenAI Agents SDK integration.
Shared by openai_agents.py and openai_agents_with_planning.py.
"""
import json
from typing import Dict, List, Any, Optional
from agents.items import ToolCallItem, MessageOutputItem, ToolCallOutputItem, ReasoningItem
from agents.items import ItemHelpers


def extract_structured_content(result: Any) -> Any:
    """
    Extract structuredContent from an MCP tool result.
    
    Handles various result formats:
    - Objects with structuredContent attribute
    - Dicts with structuredContent or content keys
    - Objects with content attribute (including lists and text attributes)
    - Fallback to the result itself
    
    Args:
        result: The result object from an MCP tool call
        
    Returns:
        The extracted structuredContent, or the result itself if extraction fails
    """
    # First priority: structuredContent attribute (only for non-dict objects)
    if not isinstance(result, dict) and hasattr(result, 'structuredContent'):
        return result.structuredContent
    
    # Second priority: dict with structuredContent or content
    if isinstance(result, dict):
        return result.get('structuredContent') or result.get('content') or result
    
    # Third priority: content attribute (only for non-dict objects)
    if not isinstance(result, dict) and hasattr(result, 'content'):
        content = result.content
        
        # Handle list of content items
        if hasattr(content, '__iter__') and not isinstance(content, str):
            content_list = []
            for item in content:
                if hasattr(item, 'text'):
                    content_list.append(item.text)
                elif isinstance(item, str):
                    content_list.append(item)
                else:
                    content_list.append(str(item))
            return '\n'.join(content_list) if content_list else None
        
        # Handle content with text attribute
        if hasattr(content, 'text'):
            return content.text
        
        # Return content as-is
        return content
    
    # Fallback: return result as-is
    return result


def extract_tools_used(result, include_nested: bool = True) -> list[dict]:
    """
    Extract tool calls from the agent run result, including nested tool calls from agent-as-tool invocations.
    
    Args:
        result: The RunResult object from Runner.run()
        include_nested: If True, includes nested tool calls from agent-as-tool invocations (e.g., query_executor -> get_schema)
        
    Returns:
        A list of dictionaries containing tool name, arguments, and nested tools for each tool call.
        Format: {
            "name": "tool_name",
            "arguments": {...},
            "nested_tools": [...]  # Only present if nested tools exist
        }
    """
    tools_used = []
    
    # Agent-as-tool names that might have nested calls
    agent_tool_names = ["query_executor", "query_planner"]
    
    # Track all items with their positions and types
    items_with_positions = []
    for idx, item in enumerate(result.new_items):
        item_type = None
        tool_name = None
        tool_arguments = None
        
        if isinstance(item, ToolCallItem):
            item_type = "tool_call"
            raw_item = item.raw_item
            
            # Handle different raw_item formats
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
        
        elif isinstance(item, ToolCallOutputItem):
            item_type = "tool_output"
        
        items_with_positions.append({
            "index": idx,
            "type": item_type,
            "tool_name": tool_name,
            "tool_arguments": tool_arguments,
            "item": item,
        })
    
    # If not including nested, return simple list
    if not include_nested:
        return [
            {"name": item["tool_name"], "arguments": item["tool_arguments"]}
            for item in items_with_positions
            if item["type"] == "tool_call" and item["tool_name"]
        ]
    
    # Build tools_used with nested structure
    # Match each tool call with its corresponding output to find nested calls
    for i, item_info in enumerate(items_with_positions):
        if item_info["type"] != "tool_call" or not item_info["tool_name"]:
            continue
        
        tool_entry = {
            "name": item_info["tool_name"],
            "arguments": item_info["tool_arguments"],
        }
        
        # Check if this is an agent-as-tool call that might have nested tools
        if item_info["tool_name"] in agent_tool_names:
            # Find the corresponding tool output for this tool call
            # Look for the next tool_output item after this tool_call
            tool_call_idx = item_info["index"]
            corresponding_output_idx = None
            
            # Find the next tool output (which should correspond to this tool call)
            for j in range(tool_call_idx + 1, len(items_with_positions)):
                if items_with_positions[j]["type"] == "tool_output":
                    corresponding_output_idx = j
                    break
            
            # Collect nested tool calls between this tool call and its output
            nested_tools = []
            if corresponding_output_idx is not None:
                # Look for tool calls between this call and its output
                for j in range(tool_call_idx + 1, corresponding_output_idx):
                    nested_item = items_with_positions[j]
                    if (nested_item["type"] == "tool_call" and 
                        nested_item["tool_name"] and
                        nested_item["tool_name"] not in agent_tool_names):
                        nested_tools.append({
                            "name": nested_item["tool_name"],
                            "arguments": nested_item["tool_arguments"],
                        })
            
            if nested_tools:
                tool_entry["nested_tools"] = nested_tools
        
        tools_used.append(tool_entry)
    
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


def build_tool_call_graph(tools_used: list[dict]) -> dict:
    """
    Build a graph structure from tool calls showing relationships between tools.
    
    Args:
        tools_used: List of tool call dictionaries with nested_tools
    
    Returns:
        A dictionary with nodes and relationships:
        {
            "nodes": [
                {"id": "tool_name", "label": "tool_name", "type": "agent"|"mcp"|"custom"}
            ],
            "relationships": [
                {"source": "parent_tool", "target": "nested_tool", "type": "CALLS"}
            ]
        }
    """
    nodes = {}
    relationships = []
    
    # Agent-as-tool names
    agent_tool_names = ["query_executor", "query_planner", "query_manager"]
    # MCP tool names
    mcp_tool_names = ["get_schema", "run_query"]
    # Custom tool names
    custom_tool_names = ["vector_search_on_chunks"]
    
    def get_tool_type(tool_name: str) -> str:
        """Determine tool type based on name."""
        if tool_name in agent_tool_names:
            return "agent"
        elif tool_name in mcp_tool_names:
            return "mcp"
        elif tool_name in custom_tool_names:
            return "custom"
        else:
            return "unknown"
    
    def add_node(tool_name: str):
        """Add a node if it doesn't exist."""
        if tool_name not in nodes:
            nodes[tool_name] = {
                "id": tool_name,
                "label": tool_name,
                "type": get_tool_type(tool_name),
            }
    
    def add_relationship(source: str, target: str):
        """Add a relationship if it doesn't exist."""
        # Check if relationship already exists
        if not any(r["source"] == source and r["target"] == target for r in relationships):
            relationships.append({
                "source": source,
                "target": target,
                "type": "CALLS",
            })
    
    # Process each tool call
    for tool in tools_used:
        tool_name = tool.get("name")
        if not tool_name:
            continue
        
        add_node(tool_name)
        
        # Add relationships to nested tools
        nested_tools = tool.get("nested_tools", [])
        for nested_tool in nested_tools:
            nested_tool_name = nested_tool.get("name")
            if nested_tool_name:
                add_node(nested_tool_name)
                add_relationship(tool_name, nested_tool_name)
    
    return {
        "nodes": list(nodes.values()),
        "relationships": relationships,
    }


def build_trace_graph_from_items(result, user_question: str) -> Dict[str, Any]:
    """
    Build a trace graph from result.new_items, similar to tracing processor output.
    
    Args:
        result: The RunResult object from Runner.run()
        user_question: The original user question
        
    Returns:
        A dictionary containing trace data with nodes and relationships for graph visualization.
        Format matches tracing processor output:
        {
            "nodes": [...],
            "relationships": [...],
            "trace_id": "...",
            "trace_name": "..."
        }
    """
    nodes = []
    relationships = []
    node_set = set()
    
    # Agent-as-tool names that represent handoffs
    agent_tool_names = ["query_executor", "query_planner", "query_manager"]
    
    # Create root trace node
    trace_id = getattr(result, "run_id", "trace_unknown")
    trace_node_id = f"trace_{trace_id}"
    
    # Extract token usage from result
    token_usage = {}
    if hasattr(result, "context_wrapper") and hasattr(result.context_wrapper, "usage"):
        usage = result.context_wrapper.usage
        token_usage = {
            "input_tokens": getattr(usage, "input_tokens", 0),
            "output_tokens": getattr(usage, "output_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        }
    
    nodes.append({
        "id": trace_node_id,
        "label": "Trace",
        "type": "trace",
        "trace_id": trace_id,
        "details": token_usage,
    })
    node_set.add(trace_node_id)
    
    # Track current parent and last tool call for linking outputs
    parent_stack = [trace_node_id]  # Stack to handle nested contexts
    current_parent = trace_node_id
    last_tool_call_id = None
    
    # Process items in order
    for idx, item in enumerate(result.new_items):
        node_id = None
        node_label = None
        node_type = None
        details = {}
        
        if isinstance(item, ToolCallItem):
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
                node_id = f"tool_call_{idx}"
                node_label = tool_name
                last_tool_call_id = node_id
                
                # Determine if this is a handoff (agent calling another agent)
                if tool_name in agent_tool_names:
                    node_type = "handoff"
                    details['target_agent'] = tool_name
                    if tool_arguments:
                        # Try to extract message from arguments
                        if isinstance(tool_arguments, dict):
                            details['message'] = tool_arguments.get('question') or tool_arguments.get('query') or tool_arguments
                        else:
                            details['message'] = tool_arguments
                        details['handoff_data'] = tool_arguments
                else:
                    node_type = "function"
                    details['function_name'] = tool_name
                    if tool_arguments:
                        # Try to parse JSON arguments if they're strings
                        if isinstance(tool_arguments, str):
                            try:
                                details['arguments'] = json.loads(tool_arguments)
                            except:
                                details['arguments'] = tool_arguments
                        else:
                            details['arguments'] = tool_arguments
        
        elif isinstance(item, ToolCallOutputItem):
            # Tool output - link to the last tool call
            output = item.output
            output_str = None
            
            if isinstance(output, str):
                output_str = output
            else:
                try:
                    output_str = json.dumps(output, indent=2)
                except:
                    output_str = str(output)
            
            # Add output as details to the last tool call node
            if last_tool_call_id:
                for node in nodes:
                    if node["id"] == last_tool_call_id:
                        node["details"]["result"] = output_str
                        break
            
            # Create a response node linked to the tool call
            if last_tool_call_id:
                node_id = f"tool_output_{idx}"
                node_label = "Tool Output"
                node_type = "response"
                details['content'] = output_str
                details['response'] = output_str
        
        elif isinstance(item, MessageOutputItem):
            # LLM response/message
            message_text = ItemHelpers.text_message_output(item)
            node_id = f"message_{idx}"
            node_label = "LLM Response"
            node_type = "generation"
            details['response'] = message_text
            details['content'] = message_text
        
        elif isinstance(item, ReasoningItem):
            # Reasoning item
            raw_item = item.raw_item
            reasoning_text = None
            
            if isinstance(raw_item, dict):
                reasoning_text = raw_item.get("content") or raw_item.get("text")
            elif hasattr(raw_item, "content"):
                reasoning_text = getattr(raw_item, "content", None)
            elif hasattr(raw_item, "text"):
                reasoning_text = getattr(raw_item, "text", None)
            
            if reasoning_text:
                node_id = f"reasoning_{idx}"
                node_label = "Reasoning"
                node_type = "generation"
                details['response'] = reasoning_text
                details['content'] = reasoning_text
        
        # Add node if we created one
        if node_id and node_label and node_type:
            nodes.append({
                "id": node_id,
                "label": node_label,
                "type": node_type,
                "trace_id": trace_id,
                "details": details,
            })
            node_set.add(node_id)
            
            # Add relationship to current parent
            relationships.append({
                "source": current_parent,
                "target": node_id,
                "type": "child",
            })
            
            # Update current parent for handoffs (they create a new context)
            if node_type == "handoff":
                parent_stack.append(node_id)
                current_parent = node_id
            # For tool outputs, link them to their tool call instead of parent
            elif node_type == "response" and last_tool_call_id:
                # Update relationship to link to tool call
                relationships[-1]["source"] = last_tool_call_id
                # If this is output for a handoff, pop the stack to return to previous parent
                if last_tool_call_id in [n["id"] for n in nodes if n.get("type") == "handoff"]:
                    if len(parent_stack) > 1:
                        parent_stack.pop()
                        current_parent = parent_stack[-1]
    
    return {
        "nodes": nodes,
        "relationships": relationships,
        "trace_id": trace_id,
        "trace_name": "Agent Execution Trace",
        "token_usage": token_usage,
    }

