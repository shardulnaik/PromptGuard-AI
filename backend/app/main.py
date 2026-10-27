import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from backend.app.config import (
    HIGH_MODEL,
    LOW_MODEL,
    MEDIUM_MODEL,
)
from backend.app.documents.parser import (
    normalize_text,
    parse_pdf,
)
from backend.app.services.pipeline import (
    PromptGuardPipeline,
)


app = FastAPI(
    title="PromptGuard-AI",
    description=(
        "Quality-aware semantic routing "
        "and cost-optimization gateway for LLM workflows."
    ),
    version="1.0.0",
)


pipeline = PromptGuardPipeline()

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def create_initial_job(
    job_id: str,
) -> dict[str, Any]:

    return {
        "job_id": job_id,
        "status": "queued",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "security": {
            "status": "pending"
        },
        "cache": {
            "status": "pending"
        },
        "analysis": {
            "status": "pending"
        },
        "routing": {
            "status": "pending"
        },
        "generation": {
            "status": "pending"
        },
        "response": None,
        "model_usage": None,
        "error": None,
    }


def update_job(
    job_id: str,
    **updates: Any,
) -> None:

    with JOBS_LOCK:
        job = JOBS.get(job_id)

        if job is None:
            return

        job.update(updates)
        job["updated_at"] = now_iso()


def progress_callback_factory(
    job_id: str,
):

    def on_progress(
        stage: str,
        status: str,
        payload: dict[str, Any] | None,
    ) -> None:

        stage_data: dict[str, Any] = {
            "status": status
        }

        if payload:
            stage_data.update(payload)

        with JOBS_LOCK:
            if job_id not in JOBS:
                return

            JOBS[job_id][stage] = stage_data
            JOBS[job_id]["updated_at"] = now_iso()

            if status == "running":
                JOBS[job_id]["status"] = "processing"

    return on_progress


def run_pipeline_job(
    job_id: str,
    user_prompt: str,
    document_bytes: bytes | None,
) -> None:

    try:
        document_text = ""

        if document_bytes:
            document_text = normalize_text(
                parse_pdf(document_bytes)
            )

        callback = progress_callback_factory(
            job_id
        )

        result = pipeline.process(
            user_prompt=user_prompt,
            document_text=document_text,
            on_progress=callback,
            document_size_bytes=(
                len(document_bytes)
                if document_bytes is not None
                else None
            ),
        )

        with JOBS_LOCK:
            JOBS[job_id]["status"] = (
                result.get(
                    "status",
                    "complete",
                )
            )

            JOBS[job_id]["response"] = result.get(
                "response"
            )

            JOBS[job_id]["model_usage"] = result.get(
                "model_usage"
            )

            JOBS[job_id]["security"] = result.get(
                "security",
                JOBS[job_id]["security"],
            )

            JOBS[job_id]["cache"] = result.get(
                "cache",
                JOBS[job_id]["cache"],
            )

            JOBS[job_id]["analysis"] = result.get(
                "analysis",
                JOBS[job_id]["analysis"],
            )

            JOBS[job_id]["routing"] = result.get(
                "routing",
                JOBS[job_id]["routing"],
            )

            JOBS[job_id]["generation"] = {
                "status": "complete"
            }

            JOBS[job_id]["updated_at"] = now_iso()

    except Exception as exc:

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = f"{type(exc).__name__}: {exc}" if "API_KEY" in str(exc) else f"Provider or pipeline error ({type(exc).__name__}). Check backend logs."
            JOBS[job_id]["updated_at"] = now_iso()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "PromptGuard-AI",
        "models": {
            "LOW": LOW_MODEL,
            "MEDIUM": MEDIUM_MODEL,
            "HIGH": HIGH_MODEL,
        },
    }


@app.post("/process")
async def start_process(
    background_tasks: BackgroundTasks,
    prompt: str = Form(default=""),
    file: UploadFile | None = File(default=None),
) -> dict[str, Any]:

    if not prompt.strip() and file is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide a prompt or upload a PDF."
            ),
        )

    document_bytes = None

    if file is not None:
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only PDF documents are supported."
                ),
            )

        document_bytes = await file.read()

        if not document_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded PDF is empty.",
            )

    job_id = str(uuid.uuid4())

    with JOBS_LOCK:
        JOBS[job_id] = create_initial_job(
            job_id
        )

    background_tasks.add_task(
        run_pipeline_job,
        job_id,
        prompt,
        document_bytes,
    )

    return {
        "job_id": job_id,
        "status": "queued",
    }


@app.get("/process/{job_id}")
def get_process(
    job_id: str,
) -> dict[str, Any]:

    with JOBS_LOCK:
        job = JOBS.get(job_id)

        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found.",
            )

        # Return a shallow copy so callers don't
        # accidentally mutate the stored state.
        return dict(job)
