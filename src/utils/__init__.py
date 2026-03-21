import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "app.yaml"


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load and cache config/app.yaml. Returns empty dict if file is missing."""
    if not _CONFIG_PATH.exists():
        return {}
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
