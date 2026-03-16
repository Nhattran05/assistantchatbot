from abc import ABC, abstractmethod


class BaseDatabase(ABC):
    """Abstract base class for all database adapters."""

    def __init__(self, config: dict):
        self.config = config
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Initialize connection pool / client."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection pool / client."""
        ...

    @abstractmethod
    async def execute(self, query: str, params: dict | None = None):
        """Execute a query and return the result."""
        ...

    @property
    def is_connected(self) -> bool:
        return self._connected
