import operator
from typing import Annotated

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class WorkflowState(TypedDict):
    """State shared across all nodes inside a Workflow graph."""

    messages: Annotated[list[BaseMessage], operator.add]
    next: str
    final_answer: str
