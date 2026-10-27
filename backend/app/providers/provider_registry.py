from backend.app.config import (
    GEMINI_API_KEY,
    GROQ_API_KEY,
    OPENAI_API_KEY,
    MAX_OUTPUT_TOKENS,
)
from backend.app.providers.openai_provider import OpenAIProvider


class GroqProvider:
    def generate(self, model: str, user_prompt: str, content: str) -> dict:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured")
        from openai import OpenAI
        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        return _chat_result(client, model, user_prompt, content)


class GeminiProvider:
    def generate(self, model: str, user_prompt: str, content: str) -> dict:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        import httpx
        prompt = user_prompt.strip()
        if content.strip():
            prompt += "\n\nDOCUMENT / CONTEXT:\n" + content.strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        response = httpx.post(
            url,
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": MAX_OUTPUT_TOKENS}},
            timeout=120.0,
        )
        if response.is_error:
            raise RuntimeError(f"Gemini provider request failed (HTTP {response.status_code})")
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini returned no candidate response")
        answer = "".join(part.get("text", "") for part in candidates[0].get("content", {}).get("parts", []))
        usage = data.get("usageMetadata", {})
        in_tokens = int(usage.get("promptTokenCount", 0))
        out_tokens = int(usage.get("candidatesTokenCount", 0))
        return {"response": answer, "input_tokens": in_tokens, "output_tokens": out_tokens, "total_tokens": int(usage.get("totalTokenCount", in_tokens + out_tokens)), "estimated_cost_usd": 0.0}


def _chat_result(client, model: str, user_prompt: str, content: str) -> dict:
    prompt = user_prompt.strip()
    if content.strip():
        prompt += "\n\nDOCUMENT / CONTEXT:\n" + content.strip()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "Answer the user's request directly and clearly. Use provided document context as the primary source."}, {"role": "user", "content": prompt}],
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    usage = response.usage
    in_tokens = getattr(usage, "prompt_tokens", 0) or 0
    out_tokens = getattr(usage, "completion_tokens", 0) or 0
    return {"response": response.choices[0].message.content or "", "input_tokens": in_tokens, "output_tokens": out_tokens, "total_tokens": in_tokens + out_tokens, "estimated_cost_usd": 0.0}


def provider_for_tier(tier: str):
    if tier == "LOW":
        return GroqProvider()
    if tier == "MEDIUM":
        return GeminiProvider()
    if tier == "HIGH":
        return OpenAIProvider()
    raise ValueError(f"Unknown routing tier: {tier}")
