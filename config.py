from pathlib import Path
from dotenv import load_dotenv
import os
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv()

PROMPTS_DIR = BASE_DIR / "prompts"

LLM_PROVIDER = "groq"
LLM_MODEL = "openai/gpt-oss-120b"
LLM_ENDPOINT = "https://api.groq.com/openai/v1"

LLM_API_KEY = os.getenv("GROQ_API_KEY")

LLM_TIMEOUT = 60

groq = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_ENDPOINT,
)
