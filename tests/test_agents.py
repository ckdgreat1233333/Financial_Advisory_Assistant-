from services.llm_service import LLMService


llm = LLMService()

print(llm.health_check())

response = llm.generate(
    "Say hello in one sentence."
)

print(response)