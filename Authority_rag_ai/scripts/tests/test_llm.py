from app.services.llm_service import LLMService


llm = LLMService()


prompt = """
You are a helpful assistant.

Question:
What is Artificial Intelligence?

Answer:
"""


print("=" * 70)
print("LLM TEST")
print("=" * 70)

response = llm.generate(prompt)

print("\nResponse:\n")
print(response)