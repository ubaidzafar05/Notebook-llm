from __future__ import annotations

import streamlit as st

from services.api_client import ApiClient, ApiError



def render(client: ApiClient) -> None:
    st.subheader("Chat")

    with st.form("session_form"):
        session_title = st.text_input("New Session Title", value="Notebook Session")
        create = st.form_submit_button("Create Session")
        if create:
            try:
                session = client.create_session(title=session_title)
                st.session_state["selected_session_id"] = session["id"]
                st.success("Session created")
            except ApiError as exc:
                st.error(str(exc))

    sessions = client.list_sessions()
    if sessions:
        selected = st.selectbox(
            "Select Session",
            options=sessions,
            format_func=lambda item: item["title"],
            key="session_selector",
        )
        st.session_state["selected_session_id"] = selected["id"]

    session_id = st.session_state.get("selected_session_id")
    if not session_id:
        st.info("Create or select a session first.")
        return

    st.markdown("### Conversation")
    try:
        messages = client.list_messages(session_id=session_id)
    except ApiError as exc:
        st.error(str(exc))
        messages = []

    for message in messages:
        role = "🧑 User" if message["role"] == "user" else "🤖 Assistant"
        st.markdown(f"**{role}**")
        st.write(message["content"])
        if message["citations"]:
            _render_citation_chips(message["citations"], key_prefix=f"history-{message['id']}")

    sources = client.list_sources()
    source_options = {f"{source['name']} ({source['id'][:6]})": source["id"] for source in sources}
    selected_source_labels = st.multiselect("Limit to Sources", options=list(source_options.keys()))
    selected_source_ids = [source_options[label] for label in selected_source_labels]

    user_message = st.text_area("Ask a question", height=120)
    if st.button("Send Message") and user_message.strip():
        answer_placeholder = st.empty()
        citations_placeholder = st.empty()
        model_info_placeholder = st.empty()
        rendered_tokens: list[str] = []
        final_payload: dict[str, object] = {}

        with st.spinner("Generating cited answer..."):
            try:
                for event in client.stream_message_events(
                    session_id=session_id,
                    message=user_message.strip(),
                    source_ids=selected_source_ids,
                ):
                    if event.get("type") == "token":
                        token_value = str(event.get("value", ""))
                        rendered_tokens.append(token_value)
                        answer_placeholder.write("".join(rendered_tokens).strip())
                    if event.get("type") == "final":
                        final_payload = event

                final_content = str(final_payload.get("content", "")).strip()
                if final_content:
                    answer_placeholder.write(final_content)
                else:
                    answer_placeholder.write("".join(rendered_tokens).strip())

                citations = final_payload.get("citations")
                if isinstance(citations, list) and citations:
                    with citations_placeholder.container():
                        st.caption("Citations")
                        _render_citation_chips(citations, key_prefix="live")

                model_info = final_payload.get("model_info")
                confidence = final_payload.get("confidence")
                if isinstance(model_info, dict):
                    summary = {"model_info": model_info, "confidence": confidence}
                    model_info_placeholder.caption(f"Response Info: {summary}")
            except ApiError as exc:
                st.error(str(exc))

    if st.button("Refresh Memory Summary"):
        try:
            summary = client.get_memory(session_id=session_id)
            st.markdown("### Memory Summary")
            st.write(summary["summary"])
            st.caption(f"Provider: {summary['provider']}")
        except ApiError as exc:
            st.error(str(exc))


def _render_citation_chips(citations: list[object], key_prefix: str) -> None:
    for index, citation_raw in enumerate(citations):
        if not isinstance(citation_raw, dict):
            continue
        source_id = str(citation_raw.get("source_id", "unknown"))
        chunk_id = str(citation_raw.get("chunk_id", "unknown"))
        page_number = citation_raw.get("page_number")
        start_timestamp = citation_raw.get("start_timestamp")
        end_timestamp = citation_raw.get("end_timestamp")

        anchor = f"chunk:{chunk_id[:8]}"
        if isinstance(page_number, int):
            anchor = f"p.{page_number}"
        elif isinstance(start_timestamp, (int, float)):
            end_part = str(end_timestamp) if isinstance(end_timestamp, (int, float)) else "?"
            anchor = f"t={start_timestamp}-{end_part}s"

        button_label = f"{source_id[:8]} • {anchor}"
        if st.button(button_label, key=f"{key_prefix}-{index}"):
            st.session_state["source_focus"] = {
                "source_id": source_id,
                "chunk_id": chunk_id,
                "page_number": page_number,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
            }
