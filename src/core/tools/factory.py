from langchain_core.tools import BaseTool

from src.core.tools.docx_export_tool import DocxExportTool

# Registry: tên tool → instance tool
TOOL_REGISTRY: dict[str, BaseTool] = {
    "docx_export": DocxExportTool(),
}


class ToolFactory:
    @staticmethod
    def get_tools(names: list[str]) -> list[BaseTool]:
        tools = []
        for name in names:
            if name not in TOOL_REGISTRY:
                raise ValueError(
                    f"Tool '{name}' not found. Available: {list(TOOL_REGISTRY.keys())}"
                )
            tools.append(TOOL_REGISTRY[name])
        return tools
