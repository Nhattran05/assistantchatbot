import json
import operator
from typing import Annotated

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.core.agents.base import BaseAgent
from src.core.llm.factory import LLMFactory
from src.core.prompts.factory import PromptFactory
from src.core.tools.docx_export_tool import DocxExportTool

_FIELD_LABELS: dict[str, str] = {
    "full_name": "Họ và tên",
    "phone_number": "Số điện thoại",
    "health_insurance_number": "Số thẻ bảo hiểm y tế",
    "medical_history": "Tiền sử bệnh lý",
    "symptoms": "Triệu chứng",
    "initial_diagnosis": "Chẩn đoán ban đầu",
    "next_treatment_plan": "Biện pháp xử lý tiếp theo",
    "notes": "Ghi chú",
    "summarize": "Tóm tắt",
}


def _format_form(filled_form_json: str) -> str:
    try:
        data = json.loads(filled_form_json)
    except json.JSONDecodeError:
        data = {}
    lines = ["Medical Examination Form", ""]
    for key, value in data.items():
        label = _FIELD_LABELS.get(key, key.replace("_", " ").title())
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


class _State(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


class DocumentExportAgent(BaseAgent):
    def build_graph(self) -> Any:
        tools = [DocxExportTool()]
        llm = LLMFactory.create(
            provider=self.config.get("llm_provider", "mega_llm"),
            model=self.config.get("llm_model"),
        )
        llm_with_tools = llm.bind_tools(tools)

        async def node_call_llm(state: _State) -> dict:
            response = await llm_with_tools.ainvoke(state["messages"])
            return {"messages": [response]}

        def route_after_llm(state: _State) -> str:
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "run_tools"
            return "__end__"

        graph = StateGraph(_State)
        graph.add_node("call_llm", node_call_llm)
        graph.add_node("run_tools", ToolNode(tools))
        graph.set_entry_point("call_llm")
        graph.add_conditional_edges(
            "call_llm",
            route_after_llm,
            {"run_tools": "run_tools", "__end__": END},
        )
        graph.add_edge("run_tools", END)
        return graph.compile()

    async def ainvoke(self, state: dict) -> dict:
        formatted_content = _format_form(state.get("filled_form", "{}"))
        system_prompt = PromptFactory.render("document_export")

        init_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Export the following content to a DOCX file:\n\n{formatted_content}"
            ),
        ]

        result = await self.graph.ainvoke({"messages": init_messages})

        # Extract the file path returned by the tool
        docx_path = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, ToolMessage) and ".docx" in msg.content:
                docx_path = msg.content.strip()
                break

        return {"docx_path": docx_path}
