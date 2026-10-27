"""Reproducibly train and evaluate the local TF-IDF tier classifier."""
import csv
from pathlib import Path

from joblib import dump
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

HERE = Path(__file__).resolve().parent
DATA = HERE / "training_data.csv"
ARTIFACT = HERE / "artifacts" / "tier_classifier.joblib"


def main() -> None:
    with DATA.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    texts = [row["text"] for row in rows]
    labels = [row["label"] for row in rows]
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True)),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)
    print(f"Examples: {len(rows)}; train: {len(x_train)}; holdout: {len(x_test)}")
    print(classification_report(y_test, predicted, labels=["LOW", "MEDIUM", "HIGH"], zero_division=0))
    print("Confusion matrix (rows=true, columns=predicted; LOW, MEDIUM, HIGH):")
    print(confusion_matrix(y_test, predicted, labels=["LOW", "MEDIUM", "HIGH"]))
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    # Save full corpus model after reporting held-out metrics for deployment.
    model.fit(texts, labels)
    dump(model, ARTIFACT)
    print(f"Saved {ARTIFACT}")


if __name__ == "__main__":
    main()
