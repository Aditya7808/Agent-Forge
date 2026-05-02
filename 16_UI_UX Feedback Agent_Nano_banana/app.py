"""Interactive Streamlit UI for the UI/UX Feedback Agent Team.

Run with:
    streamlit run app.py

Provides:
- Drag-and-drop screenshot upload
- One-click "Full audit" or "Quick critique" or "Accessibility deep-dive"
- Live chat with the coordinator agent
- Side-by-side version gallery with download buttons
- Color contrast checker in the sidebar
"""

from __future__ import annotations

import asyncio
import os
import uuid
from io import BytesIO
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# ----------------------------------------------------------------------------
# Lazy imports — only load the heavy ADK stack when the UI actually needs it
# ----------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _load_runner():
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.artifacts import InMemoryArtifactService
    from google.genai import types as gen_types

    from agent import root_agent

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    runner = Runner(
        app_name="ui_ux_feedback_team",
        agent=root_agent,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    return runner, session_service, artifact_service, gen_types


# ----------------------------------------------------------------------------
# Streamlit page setup
# ----------------------------------------------------------------------------

st.set_page_config(
    page_title="UI/UX Feedback Agent Team",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        .stChatMessage { border-radius: 12px; }
        .pill {
            display: inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: 0.78rem; background: #eef2ff; color: #3730a3;
            margin-right: 6px;
        }
        .pill.green { background: #ecfdf5; color: #065f46; }
        .pill.amber { background: #fffbeb; color: #92400e; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------

if "session_id" not in st.session_state:
    st.session_state.session_id = f"session-{uuid.uuid4().hex[:8]}"
if "user_id" not in st.session_state:
    st.session_state.user_id = "streamlit-user"
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role", "content"}
if "uploaded_artifact" not in st.session_state:
    st.session_state.uploaded_artifact = None  # filename in artifact service


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _ensure_session(session_service) -> None:
    """Create the ADK session on first use."""
    try:
        session_service.create_session(
            app_name="ui_ux_feedback_team",
            user_id=st.session_state.user_id,
            session_id=st.session_state.session_id,
        )
    except Exception:
        # Already exists — fine
        pass


async def _send_message_async(runner, gen_types, prompt_text: str, image_bytes: bytes | None):
    """Send a user message to the coordinator and stream the final reply."""
    parts = [gen_types.Part.from_text(text=prompt_text)]
    if image_bytes:
        parts.append(
            gen_types.Part(
                inline_data=gen_types.Blob(mime_type="image/png", data=image_bytes)
            )
        )

    content = gen_types.Content(role="user", parts=parts)

    final_text = ""
    async for event in runner.run_async(
        user_id=st.session_state.user_id,
        session_id=st.session_state.session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for p in event.content.parts:
                if getattr(p, "text", None):
                    final_text += p.text
    return final_text or "_(no reply)_"


def _send_message(prompt_text: str, image_bytes: bytes | None = None) -> str:
    runner, session_service, _, gen_types = _load_runner()
    _ensure_session(session_service)
    return asyncio.run(_send_message_async(runner, gen_types, prompt_text, image_bytes))


# ----------------------------------------------------------------------------
# Sidebar — controls + utilities
# ----------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🎨 UI/UX Feedback Team")
    st.caption("Multi-agent design review powered by Gemini 2.5 + Nano Banana.")

    api_present = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    if api_present:
        st.success("API key detected", icon="✅")
    else:
        st.error("Set GEMINI_API_KEY or GOOGLE_API_KEY in your .env", icon="🔑")

    st.divider()

    st.markdown("#### 📤 Upload landing page")
    uploaded = st.file_uploader(
        "Drop a screenshot",
        type=["png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
    )
    if uploaded is not None:
        st.image(uploaded, caption=uploaded.name, use_column_width=True)
        st.session_state.uploaded_bytes = uploaded.getvalue()
        st.session_state.uploaded_name = uploaded.name
    else:
        st.session_state.uploaded_bytes = None
        st.session_state.uploaded_name = None

    st.divider()

    st.markdown("#### ⚡ Quick actions")
    quick_action = st.radio(
        "Pick a workflow",
        [
            "Full audit (critic → strategy → redesign)",
            "Quick critique only",
            "Accessibility deep-dive",
            "Conversion / CRO review",
        ],
        index=0,
        label_visibility="collapsed",
    )

    if st.button("Run quick action", use_container_width=True, type="primary"):
        if not st.session_state.get("uploaded_bytes"):
            st.warning("Upload a screenshot first.")
        else:
            mapping = {
                "Full audit (critic → strategy → redesign)": "Run a full audit on this landing page: critique, strategy spec, then generate an improved redesign.",
                "Quick critique only": "Give me a quick UI/UX critique of this landing page. Skip the redesign.",
                "Accessibility deep-dive": "Run a WCAG 2.2 accessibility audit on this landing page.",
                "Conversion / CRO review": "Run a conversion-focused review on this landing page. Generate 3 A/B test hypotheses.",
            }
            prompt = mapping[quick_action]
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("Agents at work…"):
                reply = _send_message(prompt, st.session_state.uploaded_bytes)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

    st.divider()

    st.markdown("#### 🎯 Color contrast checker")
    fg = st.color_picker("Foreground", "#0A2540")
    bg = st.color_picker("Background", "#FFFFFF")
    text_size = st.selectbox("Text size", ["body", "large", "ui"], index=0)
    if st.button("Check contrast", use_container_width=True):
        from tools import estimate_color_contrast, ContrastInput

        result = estimate_color_contrast(
            ContrastInput(foreground_hex=fg, background_hex=bg, text_size=text_size)
        )
        st.markdown(result)

    st.divider()

    if st.button("🔄 Reset session", use_container_width=True):
        for key in ("session_id", "messages", "uploaded_artifact"):
            st.session_state.pop(key, None)
        st.rerun()


# ----------------------------------------------------------------------------
# Main panel
# ----------------------------------------------------------------------------

st.markdown("# 🎨 🍌 UI/UX Feedback Agent Team")
st.markdown(
    "<span class='pill green'>Multi-agent</span>"
    "<span class='pill'>Gemini 2.5 Flash</span>"
    "<span class='pill amber'>Nano Banana image gen</span>"
    "<span class='pill'>WCAG 2.2</span>",
    unsafe_allow_html=True,
)
st.caption(
    "Upload a landing page screenshot, then chat with the coordinator. "
    "It routes you to the right specialist — critic, strategist, implementer, "
    "accessibility auditor, or CRO optimizer."
)

# Render conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Show generated artifacts gallery
runner_tuple = None
if st.session_state.messages:
    runner_tuple = _load_runner()
    _, session_service, artifact_service, _ = runner_tuple
    try:
        artifact_keys = asyncio.run(
            artifact_service.list_artifact_keys(
                app_name="ui_ux_feedback_team",
                user_id=st.session_state.user_id,
                session_id=st.session_state.session_id,
            )
        )
    except Exception:
        artifact_keys = []

    if artifact_keys:
        st.markdown("### 🖼️ Generated designs")
        cols = st.columns(min(3, len(artifact_keys)))
        for i, key in enumerate(artifact_keys):
            try:
                part = asyncio.run(
                    artifact_service.load_artifact(
                        app_name="ui_ux_feedback_team",
                        user_id=st.session_state.user_id,
                        session_id=st.session_state.session_id,
                        filename=key,
                    )
                )
                if part and part.inline_data and part.inline_data.data:
                    img = Image.open(BytesIO(part.inline_data.data))
                    with cols[i % len(cols)]:
                        st.image(img, caption=key, use_column_width=True)
                        st.download_button(
                            f"⬇ Download {key}",
                            data=part.inline_data.data,
                            file_name=key,
                            mime="image/png",
                            use_container_width=True,
                            key=f"dl-{key}",
                        )
            except Exception as exc:
                st.caption(f"Could not render {key}: {exc}")

# Chat input
prompt = st.chat_input("Ask for a critique, redesign, accessibility audit…")
if prompt:
    image_bytes = st.session_state.get("uploaded_bytes")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Agents at work…"):
            reply = _send_message(prompt, image_bytes)
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
