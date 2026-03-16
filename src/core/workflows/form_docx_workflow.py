import operator
from typing import Annotated

from langchain_core.messages import BaseMessage
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.core.workflows.base import BaseWorkflow


class FormDocxWorkflowState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    user_text: str
    form_schema: dict
    filled_form: str
    docx_path: str
    next: str
    final_answer: str
    summarize: str


class FormDocxWorkflow(BaseWorkflow):
    def build_graph(self) -> Any:
        async def node_normalize(state: FormDocxWorkflowState) -> dict:
            from src.core.agents.factory import AgentFactory
            from src.utils import load_config

            config = load_config()
            agent_config = config.get("agents", {}).get("text_normalization", {})
            agent = AgentFactory.create("text_normalization", agent_config)
            result = await agent.ainvoke({
                "raw_text": state["user_text"],
                "normalized_text": "",
            })
            normalized = result.get("normalized_text", state["user_text"])
            return {"user_text": normalized}

        async def node_form_fill(state: FormDocxWorkflowState) -> dict:
            from src.core.agents.factory import AgentFactory
            from src.utils import load_config

            config = load_config()
            agent_config = config.get("agents", {}).get("form_filling", {})
            agent = AgentFactory.create("form_filling", agent_config)
            result = await agent.ainvoke({
                "user_text": state["user_text"],
                "form_schema": state.get("form_schema") or {},
                "filled_form": "",
            })
            return {"filled_form": result.get("filled_form", "")}
        
        async def node_summarize(state: FormDocxWorkflowState) -> dict:
            from src.core.agents.factory import AgentFactory
            from src.utils import load_config

            config = load_config()
            agent_config = config.get("agents", {}).get("summarization", {})
            agent = AgentFactory.create("summarization", agent_config)
            result = await agent.ainvoke({
                "text": state["filled_form"],
                "summary": "",
            })
            return {"summarize": result.get("summary", "")}
            

        async def node_export_docx(state: FormDocxWorkflowState) -> dict:
            from src.core.agents.factory import AgentFactory
            from src.utils import load_config

            config = load_config()
            agent_config = config.get("agents", {}).get("document_export", {})
            agent = AgentFactory.create("document_export", agent_config)
            result = await agent.ainvoke({"filled_form": state["filled_form"]})
            docx_path = result.get("docx_path", "")
            return {"docx_path": docx_path, "final_answer": docx_path}
        #Straight GRAPH
        graph = StateGraph(FormDocxWorkflowState)
        graph.add_node("normalize", node_normalize)
        graph.add_node("form_fill", node_form_fill)
        graph.add_node("export_docx", node_export_docx)
        graph.set_entry_point("normalize")
        graph.add_edge("normalize", "form_fill")
        graph.add_edge("form_fill", "export_docx")
        graph.add_edge("export_docx", END)
        return graph.compile()
