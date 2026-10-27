import sys
import time
from pathlib import Path

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from components.input_section import (
    render_input_section,
)
from components.analysis_panel import (
    render_analysis_panel,
)
from components.response_section import (
    render_response_section,
)
from backend.app.config import API_URL


st.set_page_config(
    page_title="PromptGuard-AI",
    page_icon="🛡️",
    layout="wide",
)


def start_job(
    prompt: str,
    uploaded_file,
) -> str:

    data = {
        "prompt": prompt or "",
    }

    files = None

    if uploaded_file is not None:

        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/pdf",
            )
        }

    response = requests.post(
        f"{API_URL}/process",
        data=data,
        files=files,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()["job_id"]


def get_job(
    job_id: str,
) -> dict:

    response = requests.get(
        f"{API_URL}/process/{job_id}",
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def main() -> None:

    st.markdown(
        "<hr>",
        unsafe_allow_html=True,
    )

    (
        prompt,
        uploaded_file,
        analyze_clicked,
        top_status_box,
    ) = render_input_section(
        status="idle"
    )

    analysis_placeholder = st.empty()

    st.markdown(
        "<hr>",
        unsafe_allow_html=True,
    )

    response_placeholder = st.empty()

    # -----------------------------------------
    # Submit
    # -----------------------------------------

    if analyze_clicked:

        if not prompt.strip() and uploaded_file is None:
            st.error(
                "Enter a prompt or upload a PDF."
            )
            return

        try:

            top_status_box.info(
                "⏳ Analyzing..."
            )

            with st.spinner(
                "Starting PromptGuard pipeline..."
            ):

                job_id = start_job(
                    prompt=prompt,
                    uploaded_file=uploaded_file,
                )

            # ---------------------------------
            # Poll backend
            # ---------------------------------

            while True:

                state = get_job(
                    job_id
                )

                render_analysis_panel(
                    state=state,
                    container=analysis_placeholder,
                )

                with response_placeholder.container():
                    render_response_section(
                        state
                    )

                current_status = state.get(
                    "status"
                )

                if current_status in {
                    "complete",
                    "blocked",
                    "failed",
                }:
                    break

                time.sleep(0.7)

            # ---------------------------------
            # Final state
            # ---------------------------------

            if current_status == "complete":
                top_status_box.success(
                    "✓ Analysis complete"
                )

            elif current_status == "blocked":
                top_status_box.error(
                    "✕ Request blocked by security layer"
                )

            else:
                top_status_box.error(
                    "✕ Processing failed"
                )

        except requests.RequestException as exc:

            top_status_box.error(
                "Backend connection failed."
            )

            st.error(
                f"Could not connect to FastAPI: {exc}"
            )

        except Exception as exc:

            top_status_box.error(
                "Something went wrong."
            )

            st.exception(exc)


if __name__ == "__main__":
    main()