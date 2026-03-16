from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


class PromptFactory:
    @staticmethod
    def render(name: str, **variables: str) -> str:
        """Load a .md prompt file and render {{variable}} placeholders."""
        prompt_file = _PROMPTS_DIR / f"{name}.md"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt '{name}' not found at {prompt_file}")
        template = prompt_file.read_text(encoding="utf-8")
        for key, value in variables.items():
            template = template.replace("{{" + key + "}}", str(value))
        return template
