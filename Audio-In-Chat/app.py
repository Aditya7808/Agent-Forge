"""Streamlit UI for Audio-In-Chat.

Launch:
    streamlit run app.py

Features:
    * OpenAI-first config wizard in the sidebar (no .env required for a quick try)
    * Drag-and-drop audio upload with validation
    * Live transcription with provider switching (OpenAI Whisper / AssemblyAI)
    * Streamed chat with retrieval-grounded answers
    * Optional source-passage display per answer
    * One-click reset of chat or full index
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import List, Optional

import streamlit as st

from audio_chat import AudioChatPipeline, Settings, __version__
from audio_chat.exceptions import (
    AudioChatError,
    AudioFileTooLargeError,
    ConfigurationError,
    UnsupportedAudioFormatError,
)

# ----------------------------- page setup ----------------------------- #

st.set_page_config(
    page_title="Audio-In-Chat",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
.main .block-container {padding-top: 2rem; padding-bottom: 6rem; max-width: 1100px;}
.stChatMessage {border-radius: 12px; padding: 0.75rem 1rem;}
.audio-card {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
    color: #f5f3ff; padding: 1rem 1.25rem; border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.08); margin-bottom: 1rem;
}
.audio-card h3 {margin: 0 0 0.25rem 0; font-size: 1rem; color: #c4b5fd;}
.audio-card p {margin: 0; font-size: 0.85rem; color: #ddd6fe;}
.stat-pill {
    display: inline-block; padding: 4px 10px; margin-right: 6px;
    background: #f1f5f9; color: #0f172a; border-radius: 999px;
    font-size: 0.78rem; font-weight: 500;
}
.source-block {
    background: #f8fafc; border-left: 3px solid #6366f1;
    padding: 0.6rem 0.9rem; border-radius: 6px; margin-top: 0.5rem;
    font-size: 0.85rem; white-space: pre-wrap;
}
hr {margin: 1rem 0;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------- session state -------------------------- #

DEFAULTS = {
    "pipeline": None,
    "messages": [],
    "ingested_files": [],
    "show_sources": False,
    "last_stats": {},
    "config_error": None,
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


# ----------------------------- helpers -------------------------------- #

def _build_settings(form: dict) -> Settings:
    """Construct a Settings object from sidebar form values."""
    s = Settings.from_env()
    s.openai_api_key = form["openai_api_key"] or s.openai_api_key
    s.openai_base_url = form["openai_base_url"] or s.openai_base_url
    s.llm_model = form["llm_model"]
    s.llm_temperature = form["llm_temperature"]
    s.embedding_model = form["embedding_model"]
    s.embedding_dim = form["embedding_dim"]
    s.transcription_provider = form["transcription_provider"]
    s.assemblyai_api_key = form["assemblyai_api_key"] or s.assemblyai_api_key
    s.qdrant_url = form["qdrant_url"] or ":memory:"
    s.qdrant_api_key = form["qdrant_api_key"] or s.qdrant_api_key
    s.qdrant_collection = form["qdrant_collection"]
    s.retrieval_top_k = form["retrieval_top_k"]
    s.chunk_size = form["chunk_size"]
    s.chunk_overlap = form["chunk_overlap"]
    return s


def _init_pipeline(settings: Settings) -> bool:
    """(Re)build the pipeline; return True on success."""
    try:
        st.session_state.pipeline = AudioChatPipeline(settings)
        st.session_state.config_error = None
        st.session_state.last_stats = st.session_state.pipeline.stats()
        return True
    except (ConfigurationError, AudioChatError) as e:
        st.session_state.pipeline = None
        st.session_state.config_error = str(e)
        return False
    except Exception as e:
        st.session_state.pipeline = None
        st.session_state.config_error = f"Unexpected error: {e}"
        return False


def _save_upload_to_tempfile(uploaded) -> str:
    suffix = Path(uploaded.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded.getbuffer())
    tmp.flush()
    tmp.close()
    return tmp.name


# ----------------------------- sidebar -------------------------------- #

with st.sidebar:
    st.title("🎧 Audio-In-Chat")
    st.caption(f"v{__version__} · Industry-grade audio RAG")

    with st.expander("🔐 LLM & embeddings (OpenAI)", expanded=True):
        openai_api_key = st.text_input(
            "OpenAI API key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            help="Used for chat, embeddings, and (optionally) Whisper transcription.",
        )
        openai_base_url = st.text_input(
            "OpenAI base URL (optional)",
            value=os.getenv("OPENAI_BASE_URL", ""),
            help="Override for Azure OpenAI, vLLM, or other OpenAI-compatible endpoints.",
        )
        llm_model = st.selectbox(
            "Chat model",
            ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "gpt-3.5-turbo"],
            index=0,
        )
        llm_temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.05)
        embedding_model = st.selectbox(
            "Embedding model",
            ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
            index=0,
        )
        embedding_dim = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }[embedding_model]

    with st.expander("🎙️ Transcription", expanded=True):
        transcription_provider = st.radio(
            "Provider",
            ["openai", "assemblyai"],
            index=0,
            horizontal=True,
            help="OpenAI Whisper is simpler. AssemblyAI adds automatic speaker labels.",
        )
        assemblyai_api_key = ""
        if transcription_provider == "assemblyai":
            assemblyai_api_key = st.text_input(
                "AssemblyAI API key",
                value=os.getenv("ASSEMBLYAI_API_KEY", ""),
                type="password",
            )

    with st.expander("🗄️ Vector store (Qdrant)", expanded=False):
        qdrant_url = st.text_input(
            "Qdrant URL",
            value=os.getenv("QDRANT_URL", ":memory:"),
            help="':memory:' for ephemeral, 'http://localhost:6333' for self-hosted, "
                 "or your Qdrant Cloud URL.",
        )
        qdrant_api_key = st.text_input(
            "Qdrant API key (cloud only)",
            value=os.getenv("QDRANT_API_KEY", ""),
            type="password",
        )
        qdrant_collection = st.text_input("Collection name", value="audio_chat_default")

    with st.expander("⚙️ Retrieval & chunking", expanded=False):
        retrieval_top_k = st.slider("Top-K retrieved chunks", 1, 15, 5)
        chunk_size = st.slider("Chunk size (chars)", 200, 2000, 800, 50)
        chunk_overlap = st.slider("Chunk overlap (chars)", 0, 500, 100, 25)
        st.session_state.show_sources = st.toggle(
            "Show source passages with each answer",
            value=st.session_state.show_sources,
        )

    apply_clicked = st.button("✅ Apply configuration", use_container_width=True, type="primary")

    if apply_clicked:
        form = dict(
            openai_api_key=openai_api_key.strip(),
            openai_base_url=openai_base_url.strip(),
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            transcription_provider=transcription_provider,
            assemblyai_api_key=assemblyai_api_key.strip(),
            qdrant_url=qdrant_url.strip(),
            qdrant_api_key=qdrant_api_key.strip(),
            qdrant_collection=qdrant_collection.strip() or "audio_chat_default",
            retrieval_top_k=retrieval_top_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        try:
            settings = _build_settings(form)
        except Exception as e:
            st.error(f"Settings error: {e}")
        else:
            with st.spinner("Initializing pipeline ..."):
                ok = _init_pipeline(settings)
            if ok:
                st.success("Pipeline ready.")
            else:
                st.error(st.session_state.config_error or "Failed to initialize.")

    if st.session_state.pipeline is not None:
        st.divider()
        cols = st.columns(2)
        if cols[0].button("🧹 Reset chat", use_container_width=True):
            st.session_state.pipeline.reset_history()
            st.session_state.messages = []
            st.toast("Chat cleared.")
        if cols[1].button("🗑️ Reset index", use_container_width=True):
            st.session_state.pipeline.reset_index()
            st.session_state.messages = []
            st.session_state.ingested_files = []
            st.toast("Index cleared.")


# ----------------------------- header --------------------------------- #

st.title("🎧 Talk to your audio")
st.markdown(
    "Upload a meeting recording, podcast, lecture, or voice note and ask anything — "
    "answers are grounded in the transcript with optional source citations."
)

if st.session_state.config_error:
    st.error(f"⚠️ Configuration issue: {st.session_state.config_error}")

if st.session_state.pipeline is None:
    st.info(
        "👈 Set your **OpenAI API key** in the sidebar and click **Apply configuration** to start.\n\n"
        "The default Qdrant mode is `:memory:` — no extra setup needed for a quick try."
    )
    st.stop()

pipeline: AudioChatPipeline = st.session_state.pipeline
stats = pipeline.stats()
st.session_state.last_stats = stats

stat_html = " ".join(
    f"<span class='stat-pill'>{k}: {v}</span>"
    for k, v in [
        ("LLM", stats["llm_model"]),
        ("Embed", stats["embedding_model"]),
        ("Dim", stats["embedding_dim"]),
        ("Transcribe", stats["transcription_provider"]),
        ("Points", stats["points"]),
    ]
)
st.markdown(stat_html, unsafe_allow_html=True)
st.divider()

# ----------------------------- ingestion ------------------------------ #

left, right = st.columns([1, 1])

with left:
    st.subheader("1. Add audio")
    uploaded = st.file_uploader(
        "Drop an audio file",
        type=[ext.lstrip(".") for ext in pipeline.settings.allowed_audio_extensions],
        accept_multiple_files=False,
        help=f"Max {pipeline.settings.max_audio_mb} MB · {' '.join(pipeline.settings.allowed_audio_extensions)}",
    )
    if uploaded is not None:
        st.audio(uploaded)
        if st.button("🚀 Transcribe & index", type="primary", use_container_width=True):
            tmp_path = _save_upload_to_tempfile(uploaded)
            try:
                with st.status("Processing audio ...", expanded=True) as status:
                    status.write("📝 Transcribing ...")
                    t0 = time.time()
                    result = pipeline.ingest_audio(tmp_path)
                    elapsed = time.time() - t0
                    status.write(
                        f"✅ Transcribed → {result['segments']} segments "
                        f"→ {result['chunks']} chunks → {result['indexed']} vectors "
                        f"({elapsed:.1f}s)"
                    )
                    status.update(label="Indexed.", state="complete")
                st.session_state.ingested_files.append(
                    {"name": uploaded.name, "summary": result}
                )
                with st.expander("Transcript preview"):
                    st.text(result.get("transcript_preview", ""))
            except (AudioFileTooLargeError, UnsupportedAudioFormatError) as e:
                st.error(f"❌ {e}")
            except AudioChatError as e:
                st.error(f"❌ Pipeline error: {e}")
            except Exception as e:
                st.exception(e)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    with st.expander("📋 Paste a transcript directly", expanded=False):
        pasted = st.text_area("Transcript text", height=160, key="pasted_text")
        if st.button("Index pasted text", use_container_width=True):
            if pasted.strip():
                try:
                    res = pipeline.ingest_text(pasted, source="pasted")
                    st.success(f"Indexed {res['indexed']} chunks.")
                    st.session_state.ingested_files.append(
                        {"name": "(pasted text)", "summary": res}
                    )
                except AudioChatError as e:
                    st.error(str(e))

with right:
    st.subheader("📂 Indexed sources")
    if not st.session_state.ingested_files:
        st.caption("Nothing indexed yet.")
    else:
        for entry in st.session_state.ingested_files:
            s = entry["summary"]
            st.markdown(
                f"<div class='audio-card'><h3>🎵 {entry['name']}</h3>"
                f"<p>{s.get('segments', '?')} segments · "
                f"{s.get('chunks', '?')} chunks · {s.get('indexed', '?')} vectors</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

st.divider()

# ----------------------------- chat ----------------------------------- #

st.subheader("2. Ask questions about the audio")

if stats["points"] == 0:
    st.info("Index some audio above to start chatting.")
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander(f"🔍 {len(msg['sources'])} source passages"):
                    for i, src in enumerate(msg["sources"], 1):
                        st.markdown(
                            f"**Source {i}** · score={src['score']:.3f}"
                            f"<div class='source-block'>{src['text']}</div>",
                            unsafe_allow_html=True,
                        )

    prompt = st.chat_input("Ask something about the audio ...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            buf: List[str] = []
            sources: Optional[List[dict]] = None
            try:
                if st.session_state.show_sources:
                    # need full retrieval result — use non-streaming with sources
                    with st.spinner("Thinking ..."):
                        out = pipeline.query_with_sources(prompt)
                    answer = out["answer"]
                    sources = out["sources"]
                    placeholder.markdown(answer)
                else:
                    for tok in pipeline.stream_query(prompt):
                        buf.append(tok)
                        placeholder.markdown("".join(buf) + "▌")
                    answer = "".join(buf)
                    placeholder.markdown(answer)
            except AudioChatError as e:
                answer = f"❌ {e}"
                placeholder.error(answer)
            except Exception as e:
                answer = f"❌ Unexpected error: {e}"
                placeholder.error(answer)

            if sources:
                with st.expander(f"🔍 {len(sources)} source passages"):
                    for i, src in enumerate(sources, 1):
                        st.markdown(
                            f"**Source {i}** · score={src['score']:.3f}"
                            f"<div class='source-block'>{src['text']}</div>",
                            unsafe_allow_html=True,
                        )

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )

# ----------------------------- footer --------------------------------- #

st.markdown(
    "<hr><center><small>🔨 Built with the <b>audio_chat</b> library · "
    "Part of <a href='https://github.com/ayusingh-54/agent-forge'>Agent Forge</a></small></center>",
    unsafe_allow_html=True,
)
