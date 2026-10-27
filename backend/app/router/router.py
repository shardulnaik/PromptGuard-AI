from functools import lru_cache
import csv
from typing import Any

from backend.app.config import ROUTER_MODEL_PATH
from backend.app.router.model_registry import get_model_for_tier

MIN_CONFIDENCE = 0.48


@lru_cache(maxsize=1)
def _load_classifier():
    try:
        import joblib
        if ROUTER_MODEL_PATH.exists():
            return joblib.load(ROUTER_MODEL_PATH)
        # Deployment fallback: train once from the bundled labelled corpus.
        # The saved artifact remains preferred for reproducible deployments.
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        dataset = ROUTER_MODEL_PATH.parent.parent / "training_data.csv"
        with dataset.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        model = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True)),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ])
        model.fit([row["text"] for row in rows], [row["label"] for row in rows])
        return model
    except Exception:
        return None


def select_tier(
    analysis: dict[str, Any],
    document_size_bytes: int | None = None,
) -> dict[str, Any]:
    prompt = str(analysis.get("routing_text", analysis.get("text", "")))
    confidence = None
    if document_size_bytes is not None and document_size_bytes >= 1_048_576:
        tier, reason = "HIGH", "Uploaded document is at least 1 MiB; size policy requires HIGH."
    else:
        classifier = _load_classifier()
        if classifier is None:
            tier, reason = "HIGH", "Local classifier artifact unavailable; conservative HIGH fallback."
        else:
            probabilities = classifier.predict_proba([prompt])[0]
            labels = classifier.classes_
            best = int(probabilities.argmax())
            confidence = float(probabilities[best])
            tier = str(labels[best])
            if confidence < MIN_CONFIDENCE:
                tier = "HIGH"
                reason = f"Uncertain local prediction ({confidence:.0%}); conservative HIGH fallback."
            else:
                reason = f"Local TF-IDF classifier selected {tier} ({confidence:.0%} confidence)."

    return {
        "tier": tier,
        "model": get_model_for_tier(tier),
        "confidence": confidence,
        "reason": reason,
    }
