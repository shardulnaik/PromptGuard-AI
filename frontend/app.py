import inspect
import sys
import time
from pathlib import Path

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import API_URL
from components.analysis_panel import show_diagnostics


st.set_page_config(
    page_title="PromptGuard-AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def start_job(prompt: str, uploaded_file) -> str:
    data = {"prompt": prompt or ""}
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
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["job_id"]


def get_job(job_id: str) -> dict:
    response = requests.get(f"{API_URL}/process/{job_id}", timeout=15)
    response.raise_for_status()
    return response.json()


def _add_styles(dark_mode: bool) -> None:
    if dark_mode:
        bg, panel, text, muted, border, accent = (
            "#0f172a", "#172236", "#f4f7ff", "#9aaac4", "#2b3a52", "#8b72ff"
        )
    else:
        bg, panel, text, muted, border, accent = (
            "#f5f7fb", "#ffffff", "#172033", "#607089", "#dce3ee", "#6650d9"
        )
    st.markdown(
        f"""
        <style>
        :root {{ color-scheme: {'dark' if dark_mode else 'light'}; }}
        [data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background:{bg}; color:{text}; }}
        [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{ visibility:hidden; height:0; }}
        [data-testid="stSidebar"] {{ background:{bg}; border-right:1px solid {border}; min-width:250px; width:20vw; }}
        [data-testid="stSidebar"] > div:first-child {{ padding:1.35rem 1.2rem; }}
        [data-testid="stMainBlockContainer"] {{ max-width:1280px; padding-top:1.4rem; padding-bottom:2rem; }}
        .pg-brand {{ font-size:1.15rem; font-weight:750; letter-spacing:-.03em; color:{text}; margin:.2rem 0 2rem; }}
        .pg-kicker {{ color:{accent}; text-transform:uppercase; letter-spacing:.12em; font-size:.74rem; font-weight:700; }}
        .pg-subtitle {{ color:{muted}; margin-top:-.5rem; }}
        [data-testid="stTextArea"] textarea, [data-testid="stChatInput"] textarea {{ background:{panel}; border-color:{border}; color:{text}; border-radius:14px; padding:.8rem; }}
        [data-testid="stFileUploader"] section {{ background:{panel}; border:1px dashed {border}; border-radius:14px; }}
        [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button {{ border-radius:11px; min-height:2.7rem; }}
        .pg-card {{ background:{panel}; border:1px solid {border}; border-radius:18px; padding:1.2rem 1.35rem; }}
        .pg-answer {{ line-height:1.72; }}
        .pg-empty {{ min-height:78vh; display:grid; place-items:center; color:{accent}; font-size:2.2rem; opacity:.78; }}
        .pg-file {{ color:{muted}; font-size:.83rem; padding:.45rem 0 .9rem; overflow-wrap:anywhere; }}
        @media (max-width: 800px) {{ [data-testid="stSidebar"] {{ min-width:unset; width:75vw; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar():
    with st.sidebar:
        st.markdown('<div class="pg-brand">🛡️ PromptGuard-AI</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload document",
            type=["pdf"],
            help="Optional. PDFs of 1 MiB or larger route to HIGH.",
            key="uploaded_pdf",
        )
        if uploaded_file:
            st.markdown(
                f'<div class="pg-file">📄 {uploaded_file.name}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("PDF optional · up to 200 MB")
        st.divider()
        chat_kwargs = {
            "key": "prompt_input",
            "max_chars": 120_000,
            "disabled": False,
        }
        if "height" in inspect.signature(st.chat_input).parameters:
            chat_kwargs["height"] = "content"
        prompt = st.chat_input("Type your prompt and press Enter", **chat_kwargs)
        return uploaded_file, prompt


def _run_request(prompt: str, uploaded_file) -> None:
    if not prompt.strip() and uploaded_file is None:
        st.session_state.request_error = "Enter a prompt or upload a PDF."
        return
    try:
        with st.spinner("Scanning, checking cache, and selecting a model…"):
            job_id = start_job(prompt, uploaded_file)
            while True:
                state = get_job(job_id)
                st.session_state.last_result = state
                if state.get("status") in {"complete", "blocked", "failed"}:
                    break
                time.sleep(0.7)
        st.session_state.request_error = None
    except requests.RequestException as exc:
        st.session_state.request_error = f"Could not connect to FastAPI: {exc}"
    except Exception as exc:
        st.session_state.request_error = f"Request failed ({type(exc).__name__})."


def _render_answer(state: dict) -> None:
    status = state.get("status")
    if status == "failed":
        st.error(state.get("error") or "The request failed.")
    elif status == "blocked":
        st.error(state.get("response") or "Request blocked by the security layer.")
    else:
        response = state.get("response")
        if not response:
            return
        st.markdown('<div class="pg-kicker">Response</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(response)
        usage = state.get("model_usage") or {}
        routing = state.get("routing") or {}
        provider_label = routing.get("display_model") or usage.get("display_model")
        if not provider_label and usage.get("cache_hit"):
            provider_label = "Semantic cache"
        if provider_label:
            st.caption(f"Served by **{provider_label}**")
    if st.button("View test results", key="view_diagnostics"):
        show_diagnostics(state)


def main() -> None:
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("request_error", None)
    _add_styles(dark_mode=True)
    uploaded_file, prompt = _render_sidebar()

    if prompt is not None:
        st.session_state.last_result = None
        st.session_state.request_error = None
        _run_request(prompt, uploaded_file)
        st.rerun()

    if st.session_state.request_error:
        st.error(st.session_state.request_error)
    state = st.session_state.last_result
    if state:
        _render_answer(state)
    else:
        st.markdown('<div class="pg-empty">✦</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
