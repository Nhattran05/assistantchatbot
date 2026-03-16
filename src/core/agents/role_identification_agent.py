"""
RoleIdentificationAgent
-----------------------
Receives a conversation transcript (list of turns with speaker_id + text),
identifies which speaker_id is the consultant and which is the customer.
Returns labeled turns and the customer's text merged for downstream processing.
"""
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.core.agents.base import BaseAgent
from src.core.llm.factory import LLMFactory

_SYSTEM_PROMPT = """You are a conversation role classifier for Vietnamese medical consultations.

You will receive a conversation transcript with turns labeled speaker_0 and speaker_1.

Your job:
1. Identify which speaker is the CONSULTANT role (mapped from doctor/bác sĩ) and which is the CUSTOMER role (mapped from patient/bệnh nhân).
2. Label every turn with the correct role.
3. Extract and merge all customer turns into a single continuous text.

Rules:
- The CONSULTANT role (doctor) typically: asks clinical questions, gives initial diagnosis, recommends next treatment.
- The CUSTOMER role (patient) typically: describes symptoms, provides personal/medical history, answers doctor questions.
- If it is genuinely unclear, label the first speaker as consultant and the second as customer.
- NEVER hallucinate. Base decisions only on the transcript content.

Return ONLY valid JSON in exactly this format, no extra text:
{
  "consultant_speaker_id": "speaker_X",
  "customer_speaker_id": "speaker_X",
  "turns": [
    { "speaker_id": "speaker_0", "role": "consultant", "start": 0.0, "end": 3.4, "text": "..." },
    { "speaker_id": "speaker_1", "role": "customer",   "start": 3.5, "end": 7.8, "text": "..." }
  ],
  "customer_text": "toàn bộ text của khách hàng ghép lại thành một đoạn"
}
"""


class _State(TypedDict):
    turns_json: str          # JSON string of raw turns from ASR
    labeled_turns_json: str  # JSON string of labeled turns (output)
    customer_text: str       # merged customer text (output)
    consultant_speaker_id: str
    customer_speaker_id: str


class RoleIdentificationAgent(BaseAgent):
    def build_graph(self) -> Any:
        llm = LLMFactory.create(
            provider=self.config.get("llm_provider", "mega_llm"),
            model=self.config.get("llm_model"),
        )

        async def node_identify(state: _State) -> dict:
            messages = [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        "Here is the conversation transcript:\n"
                        f"{state['turns_json']}\n\n"
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

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Fallback: return raw turns unchanged, treat speaker_1 as customer
                turns = json.loads(state["turns_json"])
                speaker_ids = list({t["speaker_id"] for t in turns})
                consultant_id = speaker_ids[0] if speaker_ids else "speaker_0"
                customer_id   = speaker_ids[1] if len(speaker_ids) > 1 else "speaker_1"
                labeled = [
                    {**t, "role": "consultant" if t["speaker_id"] == consultant_id else "customer"}
                    for t in turns
                ]
                customer_text = " ".join(
                    t["text"] for t in labeled if t["role"] == "customer"
                )
                return {
                    "labeled_turns_json": json.dumps(labeled, ensure_ascii=False),
                    "customer_text": customer_text,
                    "consultant_speaker_id": consultant_id,
                    "customer_speaker_id": customer_id,
                }

            return {
                "labeled_turns_json": json.dumps(data.get("turns", []), ensure_ascii=False),
                "customer_text": data.get("customer_text", ""),
                "consultant_speaker_id": data.get("consultant_speaker_id", ""),
                "customer_speaker_id": data.get("customer_speaker_id", ""),
            }

        graph = StateGraph(_State)
        graph.add_node("identify", node_identify)
        graph.set_entry_point("identify")
        graph.add_edge("identify", END)
        return graph.compile()
