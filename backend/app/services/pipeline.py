from typing import Any, Callable

from backend.app.analyzer.prompt_analyzer import PromptAnalyzer
from backend.app.cache.semantic_cache import SemanticCache
from backend.app.config import MAX_CONTENT_CHARS
from backend.app.providers.provider_registry import provider_for_tier
from backend.app.router.router import select_tier
from backend.app.security.scanner import SecurityScanner


ProgressCallback = Callable[
    [str, str, dict[str, Any] | None],
    None,
]


class PromptGuardPipeline:

    def __init__(self) -> None:
        self.security = SecurityScanner()
        self.cache = SemanticCache()
        self.analyzer = PromptAnalyzer()

    def process(
        self,
        user_prompt: str,
        document_text: str,
        on_progress: ProgressCallback,
        document_size_bytes: int | None = None,
    ) -> dict[str, Any]:

        prompt = (
            user_prompt.strip()
            if user_prompt
            else ""
        )

        document_text = (
            document_text.strip()
            if document_text
            else ""
        )

        if not prompt and document_text:
            prompt = (
                "Analyze the uploaded document "
                "and provide a clear summary of its "
                "important information."
            )

        combined_content = document_text

        full_content_for_analysis = prompt

        if document_text:
            full_content_for_analysis += (
                "\n\nDOCUMENT:\n"
                f"{document_text}"
            )

        full_content_for_analysis = (
            full_content_for_analysis[:MAX_CONTENT_CHARS]
        )

        # --------------------------------
        # 1. SECURITY
        # --------------------------------

        on_progress(
            "security",
            "running",
            None,
        )

        security_result = self.security.scan(
            full_content_for_analysis
        )

        on_progress(
            "security",
            "complete",
            security_result,
        )

        if security_result["blocked"]:
            return {
                "status": "blocked",
                "security": security_result,
                "cache": {
                    "status": "skipped"
                },
                "analysis": {
                    "status": "skipped"
                },
                "routing": {
                    "status": "blocked"
                },
                "response": (
                    "This request was blocked by "
                    "the PromptGuard security layer."
                ),
            }

        # --------------------------------
        # 2. SEMANTIC CACHE
        # --------------------------------

        on_progress(
            "cache",
            "running",
            None,
        )

        cached = self.cache.lookup(
            full_content_for_analysis
        )

        if cached:
            cache_result = {
                "status": "hit",
                "similarity": cached["similarity"],
            }

            on_progress(
                "cache",
                "complete",
                cache_result,
            )

            on_progress(
                "analysis",
                "skipped",
                {
                    "message": (
                        "Skipped because the request "
                        "was served from semantic cache."
                    )
                },
            )

            on_progress(
                "routing",
                "skipped",
                {
                    "message": (
                        "No model routing required "
                        "for a cache hit."
                    )
                },
            )

            return {
                "status": "complete",
                "security": security_result,
                "cache": cache_result,
                "analysis": {
                    "status": "skipped",
                    "message": (
                        "Cache hit — model analysis skipped."
                    ),
                },
                "routing": {
                    "status": "skipped",
                    "model": None,
                    "tier": None,
                    "reason": (
                        "Response returned directly "
                        "from semantic cache."
                    ),
                },
                "response": cached["response"],
                "model_usage": {
                    "model": None,
                    "cache_hit": True,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                },
            }

        cache_result = {
            "status": "miss",
            "similarity": None,
        }

        on_progress(
            "cache",
            "complete",
            cache_result,
        )

        # --------------------------------
        # 3. PROMPT ANALYSIS
        # --------------------------------

        on_progress(
            "analysis",
            "running",
            None,
        )

        analysis_result = self.analyzer.analyze(
            full_content_for_analysis
        )

        on_progress(
            "analysis",
            "complete",
            analysis_result,
        )

        # --------------------------------
        # 4. ROUTING
        # --------------------------------

        on_progress(
            "routing",
            "running",
            None,
        )

        routing_result = select_tier(
            {**analysis_result, "routing_text": full_content_for_analysis},
            document_size_bytes=document_size_bytes,
        )

        on_progress(
            "routing",
            "complete",
            routing_result,
        )

        # --------------------------------
        # 5. MODEL GENERATION
        # --------------------------------

        on_progress(
            "generation",
            "running",
            {
                "model": routing_result["model"],
            },
        )

        generation_result = provider_for_tier(routing_result["tier"]).generate(
            model=routing_result["model"],
            user_prompt=prompt,
            content=combined_content,
        )

        # --------------------------------
        # 6. SAVE TO CACHE
        # --------------------------------

        self.cache.save(
            text=full_content_for_analysis,
            response=generation_result["response"],
            metadata={
                "model": routing_result["model"],
                "tier": routing_result["tier"],
                "complexity": analysis_result["complexity"],
                "task_type": analysis_result["task_type"],
            },
        )

        on_progress(
            "generation",
            "complete",
            {
                **generation_result,
                "model": routing_result["model"],
            },
        )

        return {
            "status": "complete",
            "security": security_result,
            "cache": cache_result,
            "analysis": analysis_result,
            "routing": routing_result,
            "response": generation_result["response"],
            "model_usage": {
                "model": routing_result["model"],
            "provider": routing_result["provider"],
            "display_model": routing_result["display_model"],
                "cache_hit": False,
                "input_tokens": generation_result[
                    "input_tokens"
                ],
                "output_tokens": generation_result[
                    "output_tokens"
                ],
                "total_tokens": generation_result[
                    "total_tokens"
                ],
                "estimated_cost_usd": generation_result[
                    "estimated_cost_usd"
                ],
            },
        }
