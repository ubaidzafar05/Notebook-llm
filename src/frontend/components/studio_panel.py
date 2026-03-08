from __future__ import annotations

import streamlit as st

from services.api_client import ApiClient, ApiError



def render(client: ApiClient) -> None:
    st.subheader("Studio (Podcast)")

    sources = client.list_sources()
    source_options = {f"{source['name']} ({source['id'][:6]})": source["id"] for source in sources}
    selected_labels = st.multiselect("Select Sources for Podcast", options=list(source_options.keys()))
    selected_ids = [source_options[label] for label in selected_labels]
    title = st.text_input("Podcast Title", value="NotebookLM Podcast")

    if st.button("Generate Podcast"):
        if not selected_ids:
            st.warning("Select at least one source")
        else:
            try:
                result = client.create_podcast(source_ids=selected_ids, title=title)
                st.session_state["latest_podcast_id"] = result["podcast_id"]
                st.session_state["latest_podcast_source_ids"] = selected_ids
                st.session_state["latest_podcast_title"] = title
                st.success(f"Podcast job created: {result['podcast_id']}")
            except ApiError as exc:
                st.error(str(exc))

    podcast_id = st.session_state.get("latest_podcast_id")
    if podcast_id and st.button("Refresh Podcast Status"):
        try:
            podcast = client.get_podcast(podcast_id=podcast_id)
            status = podcast.get("status", "unknown")
            st.markdown("### Podcast Status Timeline")
            timeline = _timeline_for_status(status=status)
            st.write(" -> ".join(timeline))
            col1, col2, col3 = st.columns(3)
            col1.metric("Status", str(status))
            col2.metric("Duration (ms)", str(podcast.get("duration_ms") or "-"))
            col3.metric("Last Updated", str(podcast.get("updated_at") or "-"))
            st.json(podcast)
            if podcast["status"] == "completed" and podcast.get("output_path"):
                if podcast.get("duration_ms"):
                    st.caption(f"Duration: {podcast['duration_ms']} ms")
                st.markdown(f"[Download Audio]({client.podcast_audio_url(podcast_id)})")
            if podcast["status"] == "failed":
                failure_code = podcast.get("failure_code") or "UNKNOWN"
                failure_detail = podcast.get("failure_detail") or podcast.get("error_message") or "Unknown error"
                st.error(f"Failure Code: {failure_code}")
                st.caption(f"Failure Detail: {failure_detail}")
        except ApiError as exc:
            st.error(str(exc))

    if podcast_id and st.button("Retry Failed Podcast"):
        source_ids = st.session_state.get("latest_podcast_source_ids", [])
        retry_title = st.session_state.get("latest_podcast_title", title)
        if not source_ids:
            st.warning("No cached source selection found for retry.")
            return
        try:
            result = client.retry_podcast(podcast_id=podcast_id, title=retry_title)
            st.session_state["latest_podcast_id"] = result["podcast_id"]
            st.success(f"Retry started. New podcast job: {result['podcast_id']}")
        except ApiError as exc:
            st.error(str(exc))


def _timeline_for_status(status: str) -> list[str]:
    if status == "queued":
        return ["queued", "processing", "completed"]
    if status == "processing":
        return ["queued", "processing", "completed"]
    if status == "completed":
        return ["queued", "processing", "completed"]
    if status == "failed":
        return ["queued", "processing", "failed"]
    return ["queued", status]
