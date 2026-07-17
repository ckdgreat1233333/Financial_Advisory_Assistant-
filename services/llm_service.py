from pathlib import Path
from typing import Any

import requests

from config import (
    PROMPTS_DIR,
    LLM_ENDPOINT,
    LLM_MODEL,
    LLM_API_KEY,
    LLM_TIMEOUT,
)


class LLMService:
    """
    Generic Large Language Model Service.

    Responsible only for communicating with an LLM.

    It should never contain business logic.
    """

    def __init__(self):

        self.endpoint = LLM_ENDPOINT.rstrip("/")
        self.model = LLM_MODEL
        self.api_key = LLM_API_KEY
        self.timeout = LLM_TIMEOUT

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        headers = {}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.post(
            f"{self.endpoint}/api/generate",
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        return data.get("response", "").strip()

    def generate_from_template(
        self,
        template_name: str,
        **kwargs: Any,
    ) -> str:

        template_path = (
            Path(PROMPTS_DIR)
            / template_name
        )

        if not template_path.exists():
            raise FileNotFoundError(
                f"Prompt template '{template_name}' not found."
            )

        template = template_path.read_text(
            encoding="utf-8"
        )

        prompt = template.format(**kwargs)

        return self.generate(prompt)

    def health_check(self) -> bool:

        try:

            response = requests.get(
                f"{self.endpoint}/api/tags",
                timeout=5,
            )

            return response.status_code == 200

        except requests.RequestException:

            return False