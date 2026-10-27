from backend.app.analyzer.scoring import (
    fallback_analysis,
)


class PromptAnalyzer:
    def analyze(self, text: str) -> dict[str, Any]:
        """Provide local descriptive metadata; tier selection is the ML router's job."""
        return fallback_analysis(text)
