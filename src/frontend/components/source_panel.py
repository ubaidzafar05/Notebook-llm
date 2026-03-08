from __future__ import annotations

import streamlit as st

from services.api_client import ApiClient, ApiError



def render(client: ApiClient) -> None:
    st.subheader("Sources")

    uploaded_file = st.file_uploader("Upload PDF/TXT/MD/Audio", type=["pdf", "txt", "md", "mp3", "wav", "m4a", "flac"])
    if uploaded_file is not None and st.button("Ingest Uploaded File"):
        try:
            data = client.upload_source(filename=uploaded_file.name, content=uploaded_file.getvalue())
            st.success(f"Ingestion started. Job: {data['job_id']}")
            st.session_state["latest_job_id"] = data["job_id"]
        except ApiError as exc:
            st.error(str(exc))

    with st.form("url_ingest_form"):
        url = st.text_input("Web URL or YouTube URL")
        source_type = st.selectbox("URL Type", options=["web", "youtube"]) 
        submitted = st.form_submit_button("Ingest URL")
        if submitted:
            try:
                data = client.ingest_url(url=url, source_type=source_type)
                st.success(f"URL ingestion started. Job: {data['job_id']}")
                st.session_state["latest_job_id"] = data["job_id"]
            except ApiError as exc:
                st.error(str(exc))

    if st.session_state.get("latest_job_id") and st.button("Refresh Latest Job"):
        try:
            job = client.get_job(st.session_state["latest_job_id"])
            st.json(job)
            if job.get("failure_code"):
                st.error(f"Failure Code: {job['failure_code']}")
            if job.get("cancel_requested"):
                st.warning("Cancellation requested; waiting for worker acknowledgement.")
        except ApiError as exc:
            st.error(str(exc))

    st.markdown("### Source List")
    try:
        sources = client.list_sources()
        if not sources:
            st.info("No sources ingested yet.")
            return
        for source in sources:
            with st.expander(f"{source['name']} ({source['status']})"):
                st.json(source)

        st.markdown("### Source Detail Inspector")
        source_map = {f"{source['name']} ({source['id'][:6]})": source["id"] for source in sources}
        focus = st.session_state.get("source_focus", {})
        focus_source_id = focus.get("source_id") if isinstance(focus, dict) else None
        source_ids = [source["id"] for source in sources]
        default_index = source_ids.index(focus_source_id) if focus_source_id in source_ids else 0
        selected_label = st.selectbox(
            "Inspect Source",
            options=list(source_map.keys()),
            index=default_index,
            key="source_inspector",
        )
        selected_source_id = source_map[selected_label]
        detail = client.get_source_chunks(source_id=selected_source_id, limit=50, offset=0)
        focus_chunk_id = focus.get("chunk_id") if isinstance(focus, dict) else None
        for chunk in detail.get("chunks", []):
            chunk_id = chunk.get("chunk_id")
            title = f"Chunk {chunk.get('chunk_index')} • {str(chunk_id)[:8]}"
            with st.expander(title, expanded=chunk_id == focus_chunk_id):
                st.write(chunk.get("excerpt", ""))
                citation = chunk.get("citation", {})
                st.caption(f"Citation: {citation}")
    except ApiError as exc:
        st.error(str(exc))
