from abc import abstractmethod

from langchain_core.tools import BaseTool


class ProjectBaseTool(BaseTool):
    """Abstract base class for all project-specific tools."""

    @abstractmethod
    async def _arun(self, *args, **kwargs) -> str:
        """Async execution – implement this in every subclass."""
        ...

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Use _arun for async execution.")
