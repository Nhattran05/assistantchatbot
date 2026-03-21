from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.core.agents.base import BaseAgent
from src.core.llm.factory import LLMFactory
from src.core.prompts.factory import PromptFactory


class _State(TypedDict):
    raw_text: str
    normalized_text: str


class TextNormalizationAgent(BaseAgent):
    def build_graph(self) -> Any:
        llm = LLMFactory.create(
            provider=self.config.get("llm_provider", "mega_llm"),
            model=self.config.get("llm_model"),
        )

        async def node_normalize(state: _State) -> dict:
            system_prompt = PromptFactory.render("text_normalization")
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Normalize this text:\n{state['raw_text']}"),
            ]
            response = await llm.ainvoke(messages)
            normalized = response.content.strip()
            return {"normalized_text": normalized}

        graph = StateGraph(_State)
        graph.add_node("normalize", node_normalize)
        graph.set_entry_point("normalize")
        graph.add_edge("normalize", END)
        return graph.compile()
