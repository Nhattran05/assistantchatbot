from src.core.agents.base import BaseAgent
from src.core.agents.document_export_agent import DocumentExportAgent
from src.core.agents.form_filling_agent import FormFillingAgent
from src.core.agents.role_identification_agent import RoleIdentificationAgent
from src.core.agents.text_normalization_agent import TextNormalizationAgent

# Registry: tên agent → class agent
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "form_filling": FormFillingAgent,
    "document_export": DocumentExportAgent,
    "text_normalization": TextNormalizationAgent,
    "role_identification": RoleIdentificationAgent,
}


class AgentFactory:
    @staticmethod
    def create(name: str, config: dict | None = None) -> BaseAgent:
        if name not in AGENT_REGISTRY:
            raise ValueError(
                f"Agent '{name}' not found. Available: {list(AGENT_REGISTRY.keys())}"
            )
        agent_cls = AGENT_REGISTRY[name]
        return agent_cls(config or {})
