import operator
from typing import Annotated

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State shared across all nodes inside an Agent graph."""

    messages: Annotated[list[BaseMessage], operator.add]
    next: str
