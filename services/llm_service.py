from pathlib import Path
from typing import Any

from config import (
    PROMPTS_DIR,
    LLM_MODEL,
    LLM_TIMEOUT,
    groq,
)


class LLMService:
    """
    Generic Large Language Model Service.

    Responsible only for communicating with an LLM.

    It should never contain business logic.
    """

    def __init__(self):
        self.client = groq
        self.model = LLM_MODEL
        self.timeout = LLM_TIMEOUT

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content.strip()

    def generate_from_template(
        self,
        template_name: str,
        **kwargs: Any,
    ) -> str:
        template_path = Path(PROMPTS_DIR) / template_name

        if not template_path.exists():
            raise FileNotFoundError(
                f"Prompt template '{template_name}' not found."
            )

        template = template_path.read_text(encoding="utf-8")

        prompt = template.format(**kwargs)

        return self.generate(prompt)

    def health_check(self) -> bool:
        try:
            # Simple API call to verify connectivity
            self.client.models.list()
            return True

        except Exception:
            return False
