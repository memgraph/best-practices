"""
Common utilities for LLM interactions.
"""
import os
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

_openai_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


async def llm_call_json(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.1
) -> dict:
    """
    Make an LLM call with JSON response format.
    
    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt for the LLM
        model: Model to use (default: "gpt-4o")
        temperature: Temperature for the model (default: 0.1)
        
    Returns:
        Parsed JSON response as a dictionary
    """
    import json
    
    client = get_openai_client()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    return json.loads(content)

