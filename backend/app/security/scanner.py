from typing import Any

from openai import OpenAI

from backend.app.config import OPENAI_API_KEY, MODERATION_MODEL
from backend.app.security.rules import detect_prompt_injection


class SecurityScanner:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    def scan(self, text: str) -> dict[str, Any]:
        """
        Run:
        1. Local prompt-injection pattern checks
        2. OpenAI moderation

        The request is blocked if either layer returns a
        significant safety finding.
        """

        injection_findings = detect_prompt_injection(text)

        moderation_flagged = False
        moderation_error = None

        try:
            if self.client is None:
                raise RuntimeError("OpenAI moderation is not configured")
            moderation = self.client.moderations.create(
                model=MODERATION_MODEL,
                input=text,
            )

            result = moderation.results[0]
            moderation_flagged = bool(result.flagged)

        except Exception as exc:
            moderation_error = type(exc).__name__

        blocked = bool(injection_findings or moderation_flagged)

        if blocked:
            status = "blocked"
            message = "Potentially unsafe or malicious request detected."
        else:
            status = "safe"
            message = "Security checks passed."

        return {
            "status": status,
            "blocked": blocked,
            "message": message,
            "prompt_injection_detected": bool(injection_findings),
            "injection_findings_count": len(injection_findings),
            "moderation_flagged": moderation_flagged,
            "moderation_error": moderation_error,
        }
