from src.databases.base import BaseDatabase

# Registry: db type → class
DATABASE_REGISTRY: dict[str, type[BaseDatabase]] = {
    # "my_db": MyDatabase,
}


class DatabaseFactory:
    @staticmethod
    def create(db_type: str | None = None, config: dict | None = None) -> BaseDatabase:
        from src.utils import load_config

        app_config = load_config()
        db_type = db_type or app_config.get("database", {}).get("type", "")

        if db_type not in DATABASE_REGISTRY:
            raise ValueError(
                f"Database type '{db_type}' not found. Available: {list(DATABASE_REGISTRY.keys())}"
            )
        db_cls = DATABASE_REGISTRY[db_type]
        return db_cls(config or {})
