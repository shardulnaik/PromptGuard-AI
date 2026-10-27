from typing import Any

import streamlit as st


def _status_text(
    value: dict[str, Any] | None,
) -> str:

    if not value:
        return "⏳ PENDING"

    status = value.get(
        "status",
        "pending",
    )

    if status == "running":
        return "⏳ ANALYZING..."

    if status == "pending":
        return "⏳ PENDING"

    if status == "complete":
        return "✓ COMPLETE"

    if status == "miss":
        return "✕ MISS"

    if status == "hit":
        return "✓ HIT"

    if status == "skipped":
        return "— SKIPPED"

    if status == "blocked":
        return "✕ BLOCKED"

    if status == "safe":
        return "✓ PASSED"

    return status.upper()


def render_analysis_panel(
    state: dict[str, Any] | None,
    container: Any,
) -> None:

    state = state or {}

    security = state.get("security", {})
    cache = state.get("cache", {})
    analysis = state.get("analysis", {})
    routing = state.get("routing", {})

    with container.container():

        st.subheader("PromptGuard Analysis")

        col1, col2 = st.columns(2)

        with col1:

            st.markdown("**Security**")

            if security.get("blocked"):
                st.error(
                    "✕ BLOCKED"
                )
            elif security.get("status") == "safe":
                st.success(
                    "✓ PASSED"
                )
            else:
                st.info(
                    _status_text(security)
                )

            st.markdown("---")

            st.markdown("**Semantic Cache**")

            cache_status = cache.get("status")

            if cache_status == "hit":
                similarity = cache.get(
                    "similarity",
                    0,
                )

                st.success(
                    f"✓ HIT — {similarity:.2%} similarity"
                )

            elif cache_status == "miss":
                st.warning(
                    "✕ MISS"
                )

            else:
                st.info(
                    _status_text(cache)
                )

            st.markdown("---")

            st.markdown("**Task Type**")

            if analysis.get("task_type"):
                st.info(
                    str(
                        analysis["task_type"]
                    ).replace("_", " ").title()
                )
            else:
                st.info("⏳ Pending")

        with col2:

            st.markdown("**Complexity**")

            complexity = analysis.get(
                "complexity"
            )

            if complexity is not None:
                st.metric(
                    "Complexity Score",
                    f"{complexity}/10",
                )
            else:
                st.info("⏳ Pending")

            st.markdown("---")

            st.markdown("**Reasoning Requirement**")

            reasoning = analysis.get(
                "reasoning_required"
            )

            if reasoning:
                st.info(
                    str(reasoning).upper()
                )
            else:
                st.info("⏳ Pending")

            st.markdown("---")

            st.markdown("**Context Size**")

            context = analysis.get(
                "context",
                {},
            )

            tokens = context.get(
                "estimated_tokens"
            )

            if tokens is not None:
                st.info(
                    f"≈ {tokens:,} tokens"
                )
            else:
                st.info("⏳ Pending")

        st.markdown("---")

        st.subheader(
            "Routing Decision"
        )

        route_col1, route_col2 = st.columns(2)

        with route_col1:

            st.markdown("**Selected Tier**")

            tier = routing.get("tier")

            if tier:
                st.success(tier)
            else:
                st.info(
                    _status_text(routing)
                )

        with route_col2:

            st.markdown("**Selected Model**")

            model = routing.get("display_model") or routing.get("model")

            if model:
                st.code(
                    str(model),
                    language="text",
                )
            else:
                st.info(
                    "No model selected"
                )

        reason = routing.get("reason")

        if reason:
            st.markdown("**Routing Reason**")
            st.caption(reason)
        confidence = routing.get("confidence")
        if confidence is not None:
            st.caption(f"Classifier confidence: {confidence:.1%}")
