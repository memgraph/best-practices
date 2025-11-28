"""
Common utility functions for OpenAI Agents SDK integration.
Shared by openai_agents.py and openai_agents_variant.py.
"""
import json
from agents.items import ToolCallItem, MessageOutputItem, ToolCallOutputItem, ReasoningItem
from agents.items import ItemHelpers


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

