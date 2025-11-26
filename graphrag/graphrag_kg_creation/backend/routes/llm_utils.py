"""
LLM utilities for generating answers from query results.
"""
import os
import json
import logging
from typing import Any, Optional
from openai import OpenAI
from .prompts import SYSTEM_MESSAGE, create_user_message

logger = logging.getLogger(__name__)


def generate_answer(
    query_result: Any,
    question: str,
    model: str = "gpt-4o",
    temperature: float = 0.1,
    api_key: Optional[str] = None,
    fallback_to_raw: bool = True
) -> str:
    """
    Generate an answer using LLM from query result.
    
    Args:
        query_result: The query result (structuredContent) to use as context
        question: The question to answer
        model: OpenAI model to use (default: "gpt-4o")
        temperature: Temperature for generation (default: 0.1)
        api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
        fallback_to_raw: If True, return raw results if LLM fails (default: True)
        
    Returns:
        Generated answer string or fallback message
        
    Raises:
        ValueError: If no query result provided and fallback_to_raw is False
        Exception: If LLM API call fails and fallback_to_raw is False
    """
    if query_result is None:
        if fallback_to_raw:
            return f"No results found for your question: '{question}'."
        else:
            raise ValueError("No query result provided")
    
    # Get API key
    openai_api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        if fallback_to_raw:
            logger.warning("OpenAI API key not set. Returning raw results.")
            return f"Retrieved results for your question: '{question}'.\n\nResults:\n{json.dumps(query_result, indent=2)}\n\nNote: OpenAI API key not set. Set OPENAI_API_KEY environment variable to enable LLM answer generation."
        else:
            raise ValueError("OpenAI API key not set. Set OPENAI_API_KEY environment variable.")
    
    # Try to generate LLM answer
    try:
        # Convert query result to string context
        context = json.dumps(query_result, indent=2)
        user_message = create_user_message(context, question)
        
        # Call OpenAI API
        client = OpenAI(api_key=openai_api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
        )
        
        return completion.choices[0].message.content
    except Exception as e:
        # API call failed
        logger.error(f"Error calling OpenAI API: {str(e)}", exc_info=True)
        if fallback_to_raw:
            return f"Retrieved results for your question: '{question}'.\n\nResults:\n{json.dumps(query_result, indent=2)}\n\nNote: LLM answer generation failed: {str(e)}"
        else:
            raise

