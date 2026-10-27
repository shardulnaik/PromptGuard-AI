# PromptGuard-AI

PromptGuard-AI is a FastAPI backend with a Streamlit frontend for security scanning, semantic caching, local prompt tier routing, and response generation.

## Routing

After the existing security scanner and semantic cache, a local scikit-learn pipeline uses word and bigram TF-IDF features with balanced Logistic Regression to choose LOW, MEDIUM, or HIGH. LOW uses Groq, MEDIUM uses Gemini, and HIGH uses OpenAI. No LLM call is made to choose a tier. Uploads of 1 MiB (1,048,576 bytes) or larger override the classifier and use HIGH. Missing artifacts or low-confidence predictions also fall back to HIGH. Provider failures are surfaced; the application does not switch providers.

The initial balanced corpus contains 42 hand-labelled prompts (14 per tier; see `backend/app/router/training_data.csv`). It is intended as a small, transparent starting point, not a benchmark-quality dataset. Its vocabulary and task coverage are limited, so confidence is not a guarantee of correctness. Expand and review the dataset against your own workload before relying on routing decisions.

The deployable model artifact is `backend/app/router/artifacts/tier_classifier.joblib`. It is loaded once per process and should be included in deployments. If it is missing, the app trains once from the bundled corpus at first routing use; if that also fails, routing falls back to HIGH. To reproduce the stratified holdout evaluation, create the artifact, and retrain:

```powershell
python -m backend.app.router.train_router
```

The script prints per-class precision, recall, F1, support, and a confusion matrix, then fits on the full dataset and saves the deployable artifact.

## Setup

1. Create or activate a Python environment and install dependencies:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r backend\requirements.txt
   ```

2. If `.env` does not exist, copy `.env.example` to `.env`; otherwise add or update the needed variables without replacing existing secrets. Obtain Groq keys from [Groq Console](https://console.groq.com/keys), Gemini API keys from [Google AI Studio](https://aistudio.google.com/apikey), and OpenAI keys from [OpenAI API keys](https://platform.openai.com/api-keys). Keep `.env` private; it is ignored by Git.

   Required keys: `GROQ_API_KEY`, `GEMINI_API_KEY`, and `OPENAI_API_KEY`. Model names are configurable with `GROQ_MODEL`, `GEMINI_MODEL`, and `OPENAI_MODEL`. Defaults are `openai/gpt-oss-20b`, `gemini-3.5-flash-lite`, and the project's existing OpenAI model (`gpt-5.4`). Google currently lists Gemini 3.5 Flash-Lite as a free-tier text model and recommends it for new projects; actual model availability and quotas still depend on the account. Groq currently lists `openai/gpt-oss-20b` as supported, but shows usage pricing, so check the Groq account's quota and pricing. Provider failures are reported without provider fallback.

3. Start the backend from the repository root:

   ```powershell
   python -m uvicorn backend.app.main:app --reload
   ```

4. In another terminal, start the frontend:

   ```powershell
   streamlit run frontend\app.py
   ```

The API is available at `http://127.0.0.1:8000`; the health check is `/health`.

The Streamlit workspace keeps optional PDF upload and navigation in the sidebar, shows the generated answer in the main view, and opens pipeline diagnostics with **View test results**. The UI identifies the LOW provider as Groq; Groq's required API model ID remains `openai/gpt-oss-20b` internally.

## Tests

Run backend tests from the repository root with `python -m pytest`. Unit tests mock external provider requests; they do not consume API credits.
