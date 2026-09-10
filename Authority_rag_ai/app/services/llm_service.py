import os
import logging
import ollama

logger = logging.getLogger(__name__)

# Enforce IPv4 address on Windows to prevent ::1 connection refusal & set 120s timeout
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
os.environ["OLLAMA_HOST"] = OLLAMA_HOST

def get_ollama_client() -> ollama.Client:
    return ollama.Client(host=OLLAMA_HOST, timeout=120.0)

def normalize_model_tag(model_input: str) -> str:
    if not model_input:
        return "qwen2.5:3b"
    raw = str(model_input).strip().lower()
    if "qwen3.5" in raw or "qwen 3.5" in raw or "4b" in raw:
        return "qwen3.5:4b"
    elif "qwen2.5" in raw or "qwen 2.5" in raw or "3b" in raw:
        return "qwen2.5:3b"
    elif "llama" in raw or "llama3.1" in raw:
        return "llama3.1:latest"
    elif "phi" in raw or "phi3" in raw:
        return "phi3:latest"
    return "qwen2.5:3b"

def resolve_ollama_model(preferred: str = "qwen2.5:3b") -> str:
    target = normalize_model_tag(preferred)
    try:
        client = get_ollama_client()
        res = client.list()
        model_objs = res.get("models", []) if isinstance(res, dict) else getattr(res, "models", [])
        model_names = [getattr(m, "model", str(m)) for m in model_objs]
        
        if target in model_names:
            return target
        
        # Candidate check
        for candidate in ["qwen2.5:3b", "qwen3.5:4b", "llama3.1:latest", "phi3:latest"]:
            if candidate in model_names:
                return candidate
            cand_base = candidate.split(":")[0]
            for m in model_names:
                if cand_base in m:
                    return m
        if model_names:
            return model_names[0]
    except Exception as ex:
        logger.warning(f"[LLMService WARN] Could not list Ollama models at {OLLAMA_HOST} ({ex}). Defaulting to '{target}'.")
    return target

class LLMService:

    def __init__(self, model: str = None):
        self.client = get_ollama_client()
        self.model = resolve_ollama_model(model or "qwen2.5:3b")
        logger.info(f"[LLMService] Initialized active Ollama model: '{self.model}' at {OLLAMA_HOST}")

    def generate(self, prompt: str, model: str = None) -> str:
        """Generates a complete response using Ollama without mock fallbacks."""
        active_model = resolve_ollama_model(model) if model else self.model
        try:
            response = self.client.chat(
                model=active_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                stream=False,
            )
            return response.get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error(f"Ollama Call Failed for model '{active_model}': {str(e)}", exc_info=True)
            raise RuntimeError(f"Ollama Call Failed for model '{active_model}': {str(e)}") from e

    def generate_stream(self, prompt: str, model: str = None):
        """Streams response tokens directly from Ollama."""
        active_model = resolve_ollama_model(model) if model else self.model
        try:
            stream = self.client.chat(
                model=active_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                stream=True,
            )

            for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Ollama Streaming Failed for model '{active_model}': {str(e)}", exc_info=True)
            raise RuntimeError(f"Ollama Streaming Failed for model '{active_model}': {str(e)}") from e