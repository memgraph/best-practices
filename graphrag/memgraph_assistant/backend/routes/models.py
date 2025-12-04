"""
Pydantic models for chat routes.
"""
from pydantic import BaseModel
from enum import Enum


class ChatMode(str, Enum):
    """Chat mode enumeration."""
    AGENT = "agent"  # Can execute queries, write operations require approval
    ASK = "ask"  # Only proposes plans, doesn't execute write operations


class ChatRequest(BaseModel):
    """Request model for chat queries."""
    question: str
    session_id: str | None = None
    mode: ChatMode = ChatMode.AGENT  # Default to agent mode


class ApproveRequest(BaseModel):
    """Request model for approving queries."""
    query: str  # The query to approve and execute
    session_id: str | None = None

