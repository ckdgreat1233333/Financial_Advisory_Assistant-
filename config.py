from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

PROMPTS_DIR = BASE_DIR / "prompts"


# LLM Configuration

LLM_PROVIDER = "local"

LLM_MODEL = "llama3.2:3b"

LLM_ENDPOINT = "http://localhost:11434"

LLM_API_KEY = ""

LLM_TIMEOUT = 60