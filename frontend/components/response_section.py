from typing import Any

import streamlit as st


def render_response_section(
    state: dict[str, Any] | None,
) -> None:

    st.subheader("Response")

    if not state:
        st.info(
            "Your final response will appear here."
        )
        return

    status = state.get(
        "status"
    )

    if status == "failed":

        st.error(
            state.get(
                "error",
                "An unknown error occurred.",
            )
        )
        return

    if status == "blocked":

        st.error(
            state.get(
                "response",
                "Request blocked.",
            )
        )
        return

    response = state.get(
        "response"
    )

    if not response:
        st.info(
            "Waiting for the response..."
        )
        return

    st.markdown(response)

    st.markdown("---")

    usage = state.get(
        "model_usage"
    ) or {}

    cols = st.columns(4)

    with cols[0]:
        st.metric(
            "Model",
            usage.get("display_model") or usage.get("model", "Cache"),
        )

    with cols[1]:
        st.metric(
            "Input Tokens",
            f"{usage.get('input_tokens', 0):,}",
        )

    with cols[2]:
        st.metric(
            "Output Tokens",
            f"{usage.get('output_tokens', 0):,}",
        )

    with cols[3]:
        st.metric(
            "Estimated Cost",
            f"${usage.get('estimated_cost_usd', 0.0):.4f}",
        )
