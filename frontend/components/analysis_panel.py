from typing import Any

import streamlit as st


def _value(value: Any, default: str = "—") -> str:
    if value is None or value == "":
        return default
    return str(value)


@st.dialog("PromptGuard test results", width="large")
def show_diagnostics(state: dict[str, Any]) -> None:
    """Show compact pipeline diagnostics without pushing the answer down-page."""
    state = state or {}
    security = state.get("security") or {}
    cache = state.get("cache") or {}
    analysis = state.get("analysis") or {}
    routing = state.get("routing") or {}
    context = analysis.get("context") or {}

    first = st.columns(3)
    first[0].metric("Security", "BLOCKED" if security.get("blocked") else _value(security.get("status"), "pending").upper())
    cache_status = _value(cache.get("status"), "pending").upper()
    if cache.get("similarity") is not None:
        cache_status += f" · {cache['similarity']:.0%}"
    first[1].metric("Semantic cache", cache_status)
    first[2].metric("Task type", _value(analysis.get("task_type")).replace("_", " ").title())

    second = st.columns(3)
    complexity = analysis.get("complexity")
    second[0].metric("Complexity", f"{complexity}/10" if complexity is not None else "—")
    second[1].metric("Reasoning", _value(analysis.get("reasoning_required")).upper())
    tokens = context.get("estimated_tokens")
    second[2].metric("Context size", f"~{tokens:,} tokens" if tokens is not None else "—")

    third = st.columns(3)
    third[0].metric("Selected tier", _value(routing.get("tier")))
    third[1].metric("Provider / model", _value(routing.get("display_model"), "No generation"))
    confidence = routing.get("confidence")
    third[2].metric("Classifier confidence", f"{confidence:.1%}" if confidence is not None else "—")

    reason = routing.get("reason")
    if reason:
        st.caption(reason)
