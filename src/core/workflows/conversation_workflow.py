"""
ConversationWorkflow
--------------------
Full pipeline:
  WAV file
    → Diarization (who spoke when)
    → ASR (what they said)
    → RoleIdentification (consultant vs customer)
    → TextNormalization (spoken numbers/symbols → standard text)
    → FormFilling (extract schema fields)
    → DocumentExport (generate DOCX)
"""
import json
import operator
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.core.workflows.base import BaseWorkflow


class ConversationWorkflowState(TypedDict):
    # Input
    audio_path: str

    # Intermediate
    messages: Annotated[list[BaseMessage], operator.add]
    turns_json: str              # raw ASR turns JSON
    labeled_turns_json: str      # role-labeled turns JSON
    consultant_speaker_id: str
    customer_speaker_id: str
    customer_text: str           # merged customer speech
    normalized_text: str         # after text normalization
    user_text: str               # alias passed into form filling
    form_schema: dict
    filled_form: str             # JSON string

    # Output
    docx_path: str
    final_answer: str


class ConversationWorkflow(BaseWorkflow):
    def build_graph(self) -> Any:

        # ----------------------------------------------------------------
        # Node 1: Diarization + ASR  (runs in a thread — blocking I/O)
        # ----------------------------------------------------------------
        async def node_transcribe(state: ConversationWorkflowState) -> dict:
            import asyncio
            from src.services.diarization_service import DiarizationService
            from src.services.asr_service import ASRService

            def _run():
                diar = DiarizationService()
                asr  = ASRService()
                segments = diar.diarize(state["audio_path"])
                turns    = asr.transcribe_segments(state["audio_path"], segments)
                return turns

            turns = await asyncio.get_event_loop().run_in_executor(None, _run)
            return {"turns_json": json.dumps(turns, ensure_ascii=False)}

        # ----------------------------------------------------------------
        # Node 2: Role Identification
        # ----------------------------------------------------------------
        async def node_identify_roles(state: ConversationWorkflowState) -> dict:
            from src.core.agents.factory import AgentFactory
            from src.utils import load_config

            cfg = load_config()
            agent = AgentFactory.create(
                "role_identification",
                cfg.get("agents", {}).get("role_identification", {}),
            )
            result = await agent.ainvoke({
                "turns_json": state["turns_json"],
                "labeled_turns_json": "",
                "customer_text": "",
                "consultant_speaker_id": "",
                "customer_speaker_id": "",
            })
            labeled_turns_json = result.get("labeled_turns_json", "[]")

            # Build a full dialogue text that includes both sides so medical
            # fields like initial diagnosis / next treatment can be extracted.
            dialogue_text = ""
            try:
                labeled_turns = json.loads(labeled_turns_json)
                lines: list[str] = []
                for turn in labeled_turns:
                    role = str(turn.get("role", "")).strip().lower()
                    speaker = "Bác sĩ" if role == "consultant" else "Bệnh nhân"
                    text = str(turn.get("text", "")).strip()
                    if text:
                        lines.append(f"{speaker}: {text}")
                dialogue_text = "\n".join(lines)
            except Exception:
                dialogue_text = ""

            if not dialogue_text:
                dialogue_text = result.get("customer_text", "")

            return {
                "labeled_turns_json":   labeled_turns_json,
                "customer_text":        result.get("customer_text", ""),
                "consultant_speaker_id": result.get("consultant_speaker_id", ""),
                "customer_speaker_id":  result.get("customer_speaker_id", ""),
                "user_text":            dialogue_text,
            }

        # ----------------------------------------------------------------
        # Node 3: Text Normalization (on full doctor+patient dialogue)
        # ----------------------------------------------------------------
        async def node_normalize(state: ConversationWorkflowState) -> dict:
            from src.core.agents.factory import AgentFactory
            from src.utils import load_config

            cfg = load_config()
            agent = AgentFactory.create(
                "text_normalization",
                cfg.get("agents", {}).get("text_normalization", {}),
            )
            result = await agent.ainvoke({
                "raw_text": state["user_text"],
                "normalized_text": "",
            })
            normalized = result.get("normalized_text", state["user_text"])
            return {"normalized_text": normalized, "user_text": normalized}

        # ----------------------------------------------------------------
        # Node 4: Form Filling
        # ----------------------------------------------------------------
        async def node_form_fill(state: ConversationWorkflowState) -> dict:
            from src.core.agents.factory import AgentFactory
            from src.utils import load_config

            cfg = load_config()
            agent = AgentFactory.create(
                "form_filling",
                cfg.get("agents", {}).get("form_filling", {}),
            )
            result = await agent.ainvoke({
                "user_text": state["user_text"],
                "form_schema": state.get("form_schema") or {},
                "filled_form": "",
            })
            return {"filled_form": result.get("filled_form", "")}

        # ----------------------------------------------------------------
        # Node 5: Document Export
        # ----------------------------------------------------------------
        async def node_export_docx(state: ConversationWorkflowState) -> dict:
            from src.core.agents.factory import AgentFactory
            from src.utils import load_config

            cfg = load_config()
            agent = AgentFactory.create(
                "document_export",
                cfg.get("agents", {}).get("document_export", {}),
            )
            result = await agent.ainvoke({"filled_form": state["filled_form"]})
            docx_path = result.get("docx_path", "")
            return {"docx_path": docx_path, "final_answer": docx_path}

        # ----------------------------------------------------------------
        # Build graph
        # ----------------------------------------------------------------
        graph = StateGraph(ConversationWorkflowState)
        graph.add_node("transcribe",      node_transcribe)
        graph.add_node("identify_roles",  node_identify_roles)
        graph.add_node("normalize",       node_normalize)
        graph.add_node("form_fill",       node_form_fill)
        graph.add_node("export_docx",     node_export_docx)

        graph.set_entry_point("transcribe")
        graph.add_edge("transcribe",     "identify_roles")
        graph.add_edge("identify_roles", "normalize")
        graph.add_edge("normalize",      "form_fill")
        graph.add_edge("form_fill",      "export_docx")
        graph.add_edge("export_docx",    END)

        return graph.compile()
