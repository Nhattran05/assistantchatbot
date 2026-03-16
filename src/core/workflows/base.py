from abc import ABC, abstractmethod
from typing import Any


class BaseWorkflow(ABC):
    """Abstract base class for all multi-agent Workflows."""

    def __init__(self, config: dict):
        self.config = config
    _graph: Any | None = None

    @abstractmethod
    def build_graph(self) -> Any:
        """Build and return the compiled LangGraph workflow."""
        ...

    @property
    def graph(self) -> Any:
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph

    async def ainvoke(self, state: dict) -> dict:
        return await self.graph.ainvoke(state)
