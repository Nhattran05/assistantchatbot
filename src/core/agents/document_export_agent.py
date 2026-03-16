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

        init_messages = [
            SystemMessage(
                content=(
                    "You are a document export assistant. "
                    "Call the docx_export tool with the provided content to generate the DOCX file. "
                    "Do not modify the content."
                    """You should fill in this form .md form:
                    # PHIẾU KHÁM BỆNH
                    ## I. Thông tin hành chính
                    * **Họ và tên người bệnh :** ........................................................................
                    * **Số điện thoại :** ................................................................................
                    * **Mã số Bảo hiểm Y tế :** ................................................

                    ## II. Thông tin lâm sàng
                    * **Tiền sử bệnh lý :** * [Ghi chú các bệnh lý đã mắc, dị ứng thuốc, phẫu thuật trước đây...]
                    * **Triệu chứng hiện tại :** * [Mô tả các triệu chứng cơ năng và thực thể người bệnh đang gặp phải...]

                    ## III. Chẩn đoán và Hướng xử trí
                    * **Chẩn đoán ban đầu :** * [Ghi rõ chẩn đoán sơ bộ dựa trên triệu chứng và tiền sử...]
                    * **Kế hoạch điều trị tiếp theo :** * [Chỉ định cận lâm sàng, đơn thuốc, hoặc hẹn tái khám...]

                    ## IV. Thông tin bổ sung
                    * **Tóm tắt ca bệnh :** * [Gắn gọn tình trạng bệnh nhân, điểm cốt lõi cần lưu ý...]
                    * **Ghi chú thêm :** * [Những lưu ý đặc biệt khác về bệnh nhân hoặc quá trình thăm khám...]

                    ---
                    **Ngày khám:** ....../....../20... 
                    **Chữ ký Bác sĩ điều trị:**
                    Then use the tool to export the above content to a DOCX file. Return only the file path of the generated DOCX as a string, without any additional text or formatting.
                    If "không có " or "không có gì" is mentioned in the content, it means the field is empty and should be left blank in the DOCX."""

                )
            ),
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
