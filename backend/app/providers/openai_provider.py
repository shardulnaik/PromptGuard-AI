from typing import Any

from openai import OpenAI

from backend.app.config import (
    OPENAI_API_KEY,
    MAX_OUTPUT_TOKENS,
)


MODEL_REASONING_EFFORT = {
    "gpt-5.4-nano": "low",
    "gpt-5.4-mini": "medium",
    "gpt-5.4": "high",
}


class OpenAIProvider:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    def generate(
        self,
        model: str,
        user_prompt: str,
        content: str,
    ) -> dict[str, Any]:

        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        reasoning_effort = MODEL_REASONING_EFFORT.get(
            model,
            "medium",
        )

        generation_input = user_prompt.strip()

        if content.strip():
            generation_input += (
                "\n\n"
                "DOCUMENT / CONTEXT:\n"
                "----------------------\n"
                f"{content.strip()}"
            )

        system_instruction = """
You are the final response model inside PromptGuard-AI.

Answer the user's request directly and clearly.

If document/context is provided, use it as the primary source.
Do not talk about PromptGuard-AI unless the user asks about it.
Do not mention internal routing, model tiers, or security checks
in the answer unless explicitly requested.
"""

        response = self.client.responses.create(
            model=model,
            instructions=system_instruction,
            input=generation_input,
            reasoning={
                "effort": reasoning_effort
            },
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        usage = getattr(response, "usage", None)

        input_tokens = getattr(
            usage,
            "input_tokens",
            0,
        ) or 0

        output_tokens = getattr(
            usage,
            "output_tokens",
            0,
        ) or 0

        total_tokens = getattr(
            usage,
            "total_tokens",
            input_tokens + output_tokens,
        ) or (
            input_tokens + output_tokens
        )

        # Current standard API pricing per 1M tokens.
        # Kept here only for demo metrics.
        pricing = {
            "gpt-5.4-nano": {
                "input": 0.20,
                "output": 1.25,
            },
            "gpt-5.4-mini": {
                "input": 0.75,
                "output": 4.50,
            },
            "gpt-5.4": {
                "input": 2.50,
                "output": 15.00,
            },
        }

        model_price = pricing.get(
            model,
            {
                "input": 0.0,
                "output": 0.0,
            },
        )

        estimated_cost = (
            (input_tokens / 1_000_000)
            * model_price["input"]
            +
            (output_tokens / 1_000_000)
            * model_price["output"]
        )

        return {
            "response": response.output_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(
                estimated_cost,
                6,
            ),
        }
