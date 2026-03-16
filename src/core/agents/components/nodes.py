from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode

from src.core.agents.components.states import AgentState


async def node_call_llm(state: AgentState, llm_with_tools) -> dict:
    """Call the LLM (with tools bound) and append the response to messages."""
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


def route_after_llm(state: AgentState) -> str:
    """Route to tool execution or end based on last message."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "run_tools"
    return "__end__"


def build_tool_node(tools: list) -> ToolNode:
    """Create a LangGraph ToolNode from a list of tools."""
    return ToolNode(tools)
