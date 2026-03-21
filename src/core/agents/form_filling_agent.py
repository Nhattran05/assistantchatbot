import json

from langchain_core.messages import HumanMessage, SystemMessage
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.core.agents.base import BaseAgent
from src.core.llm.factory import LLMFactory
from src.core.prompts.factory import PromptFactory

DEFAULT_SCHEMA: dict = {
    "full_name": "",
    "phone_number": "",
    "health_insurance_number": "",
    "medical_history": "",
    "symptoms": "",
    "initial_diagnosis": "",
    "next_treatment_plan": "",
    "notes": "",
    "summarize": "",
}


class _State(TypedDict):
    user_text: str
    form_schema: dict
    filled_form: str


class FormFillingAgent(BaseAgent):
    def build_graph(self) -> Any:
        llm = LLMFactory.create(
            provider=self.config.get("llm_provider", "mega_llm"),
            model=self.config.get("llm_model"),
        )

        async def node_extract(state: _State) -> dict:
            schema = state.get("form_schema") or DEFAULT_SCHEMA
            schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
            system_prompt = PromptFactory.render("form_filling")
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=(
                        f"Form schema:\n{schema_str}\n\n"
                        f"User text:\n{state['user_text']}\n\n"
                        "Return JSON only."
                    )
                ),
            ]
            response = await llm.ainvoke(messages)
            raw = response.content.strip()

            # Strip markdown fences if present
            if raw.startswith("```"):
                lines = raw.splitlines()
                inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                raw = "\n".join(inner).strip()

            # Validate JSON; fallback to all "không có"
            try:
                json.loads(raw)
            except json.JSONDecodeError:
                raw = json.dumps({k: "không có" for k in schema}, ensure_ascii=False)

            return {"filled_form": raw}

        graph = StateGraph(_State)
        graph.add_node("extract", node_extract)
        graph.set_entry_point("extract")
        graph.add_edge("extract", END)
        return graph.compile()
