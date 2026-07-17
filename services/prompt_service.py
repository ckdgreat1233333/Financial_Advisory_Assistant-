from __future__ import annotations

from pathlib import Path
from typing import Any


class PromptService:
    """
    Loads and formats prompt templates from text files.

    Example:
        prompt = PromptService()

        final_prompt = prompt.load(
            "policy.txt",
            question="Can I apply for a loan?",
            context="Minimum salary is ₹30,000."
        )
    """

    def __init__(self, prompt_directory: str = "prompts") -> None:
        self.prompt_dir = Path(prompt_directory)

        if not self.prompt_dir.exists():
            raise FileNotFoundError(
                f"Prompt directory '{self.prompt_dir}' does not exist."
            )

    def load(self, template_name: str, **kwargs: Any) -> str:
        """
        Load a prompt template and replace placeholders.

        Example:
            Question:
            {question}

            Context:
            {context}
        """

        template_path = self.prompt_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(
                f"Prompt template '{template_name}' not found."
            )

        template = template_path.read_text(
            encoding="utf-8"
        )

        try:
            return template.format(**kwargs)

        except KeyError as exc:
            raise ValueError(
                f"Missing template variable: {exc}"
            ) from exc

    def exists(self, template_name: str) -> bool:
        """Check whether a template exists."""
        return (self.prompt_dir / template_name).exists()

    def list_templates(self) -> list[str]:
        """Return all available prompt templates."""

        return sorted(
            file.name
            for file in self.prompt_dir.glob("*.txt")
        )