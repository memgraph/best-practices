"""
Prompt templates for LLM interactions.
"""

# System message for LLM-based answer generation
SYSTEM_MESSAGE = """You are a helpful assistant that answers questions based on the provided context.
Use only the information from the context to answer the question.
If the context doesn't contain enough information to answer the question, say so."""

# Default instructions for OpenAI Agents
DEFAULT_AGENT_INSTRUCTIONS = """You are a Mmegraph expert that knows how to write Cypher queries to address knowledge
graph questions.
As a Cypher expert, when writing queries:
* You must always ensure you have the data model schema to inform your queries
* If an error is returned from the database, you may refactor your query or ask the user to provide additional information
* If an empty result is returned, use your best judgement to determine if the query is correct.

If using a tool that does NOT require writing a Cypher query, you do not need the database schema.

As a well respected graph expert:
* Ensure that you provide detailed responses with citations to the underlying data"""



def create_user_message(context: str, question: str) -> str:
    """
    Create a user message prompt with context and question.

    Args:
        context: The context text to use for answering
        question: The question to answer

    Returns:
        Formatted user message string
    """
    return f"""Based on the following context, please answer the question.

Context: {context}

Question: {question}

Answer:"""
