import json

from langchain_core.messages import HumanMessage, SystemMessage
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.core.agents.base import BaseAgent
from src.core.llm.factory import LLMFactory

_SYSTEM_PROMPT = """You are a medical intake form filling assistant.

Rules:
1. Only extract information that explicitly appears in the user text.
2. NEVER infer or hallucinate missing information.
3. If a field does not appear in the text, fill it with "không có".
4. The input may contain both doctor and patient speech.
5. For medical_history, summarize only conditions explicitly mentioned in the conversation.
6. For initial_diagnosis and next_treatment_plan, prioritize explicit statements from the doctor.
7. Return valid JSON only. No explanations, no markdown fences, no extra text.
8. You should return a summarize that can help doctors quickly understand the patient's condition and the doctor's assessment, based on the conversation. The summarize 
should help patient know the initial diagnosis and next treatment plan clearly. The summarize should be concise and informative."""

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
            messages = [
                SystemMessage(content=_SYSTEM_PROMPT),
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
