from src.core.workflows.base import BaseWorkflow
from src.core.workflows.conversation_workflow import ConversationWorkflow
from src.core.workflows.form_docx_workflow import FormDocxWorkflow

# Registry: tên workflow → class workflow
WORKFLOW_REGISTRY: dict[str, type[BaseWorkflow]] = {
    "form_docx_workflow": FormDocxWorkflow,
    "conversation_workflow": ConversationWorkflow,
}


class WorkflowFactory:
    @staticmethod
    def create(name: str | None = None, config: dict | None = None) -> BaseWorkflow:
        from src.utils import load_config

        app_config = load_config()
        workflow_name = name or app_config.get("workflows", {}).get("default", "")

        if workflow_name not in WORKFLOW_REGISTRY:
            raise ValueError(
                f"Workflow '{workflow_name}' not found. Available: {list(WORKFLOW_REGISTRY.keys())}"
            )
        workflow_cls = WORKFLOW_REGISTRY[workflow_name]
        workflow_config = config or app_config.get("workflows", {}).get(workflow_name, {})
        return workflow_cls(workflow_config)
