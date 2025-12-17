"""
Prompts for LLM-based content processing.
"""

# Keyword extraction prompts
KEYWORDS_SYSTEM_PROMPT = (
    "You extract keywords from Memgraph documentation. "
    "Return ONLY a raw JSON array like [\"keyword1\", \"keyword2\"]. "
    "No markdown, no code blocks, no explanation."
)

KEYWORDS_USER_PROMPT_TEMPLATE = (
    "Extract 3-5 keywords from this content:\n\n"
    "{content}\n\n"
    "Return ONLY: [\"keyword1\", \"keyword2\", ...]"
)

# Summary extraction prompts
SUMMARY_SYSTEM_PROMPT = (
    "You are a helpful assistant that creates concise summaries of "
    "Memgraph's documentation content. Return only the summary text, "
    "nothing else."
)

SUMMARY_USER_PROMPT_TEMPLATE = (
    "Create a brief summary (2-3 sentences) of this Memgraph documentation "
    "page:\n\n"
    "{content}"
)

# Cypher query extraction prompts
CYPHER_QUERIES_SYSTEM_PROMPT = (
    "You are a helpful assistant that extracts Cypher queries from documentation. "
    "Always return valid JSON with a 'queries' key containing an array."
)

CYPHER_QUERIES_USER_PROMPT_TEMPLATE = (
    "Extract all Cypher queries from the following Memgraph documentation page.\n\n"
    "URL: {url}\n"
    "Entity/Concept: {entity_id}\n\n"
    "Page Content:\n"
    "{content}\n\n"
    "Please extract all Cypher queries found in this documentation page and return them as a JSON object with a \"queries\" key containing an array. For each query, provide:\n"
    "1. entity_id: The concept/feature being explained (e.g., \"pagerank\", \"bfs\", \"shortest_path\")\n"
    "2. query: The raw Cypher query exactly as shown in the documentation\n"
    "3. description: A brief description of what the query does\n\n"
    "Return ONLY a valid JSON object in this format:\n"
    "{{\n"
    "  \"queries\": [\n"
    "    {{\n"
    "      \"entity_id\": \"concept_name\",\n"
    "      \"query\": \"CALL pagerank.get() YIELD node, rank;\",\n"
    "      \"description\": \"Calculates the PageRank for the nodes in the graph.\"\n"
    "    }},\n"
    "    ...\n"
    "  ]\n"
    "}}\n\n"
    "If no queries are found, return {{\"queries\": []}}.\n\n"
    "Important:\n"
    "- Extract queries exactly as written (preserve formatting, line breaks, etc.)\n"
    "- Include all queries: examples, setup queries, result queries, etc.\n"
    "- The entity_id should represent the main concept being explained on this page\n"
    "- Return valid JSON only, no markdown formatting or explanations"
)
