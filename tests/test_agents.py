import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.llm_service import LLMService


llm = LLMService()

print(llm.health_check())

response = llm.generate(
    "Summarize the coverage of an auto insurance claim in one sentence."
)

print(response)
