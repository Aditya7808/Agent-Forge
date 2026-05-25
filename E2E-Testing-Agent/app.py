"""
Streamlit App for E2E Testing Agent
====================================
Premium web interface for the E2E Testing Agent.
Allows users to describe tests in natural language and
generates + executes Playwright E2E test scripts.

Usage:
    streamlit run app.py
"""

import streamlit as st
import os
import sys
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Playwright Browser Installation (for Streamlit Cloud)
# ---------------------------------------------------------------------------
@st.cache_resource
def install_playwright_browsers():
    """Install Playwright Chromium browser binaries on first run (Streamlit Cloud)."""
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception:
        pass  # Silently continue — tests won't run but UI will still load

install_playwright_browsers()

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="E2E Testing Agent",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    .main .block-container {
        padding-top: 2rem;
        max-width: 1100px;
    }

    /* Hero Header */
    .hero-header {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
    }
    .hero-header h1 {
        font-family: 'Inter', sans-serif;
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .hero-subtitle {
        color: #888;
        font-size: 1.05rem;
        font-family: 'Inter', sans-serif;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid #e2e5f1;
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .metric-card .label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-card .value {
        font-size: 1.3rem;
        font-weight: 700;
        color: #333;
        margin-top: 0.3rem;
    }

    /* Action list */
    .action-item {
        background: #f8f9ff;
        border-left: 3px solid #667eea;
        padding: 0.6rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.92rem;
        color: #444;
    }

    /* Report section */
    .report-container {
        background: #fafbff;
        border: 1px solid #e2e5f1;
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown label,
    section[data-testid="stSidebar"] .stMarkdown span {
        color: #e0e0e0 !important;
    }

    /* Status badges */
    .badge-pass {
        background: #d4edda;
        color: #155724;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-fail {
        background: #f8d7da;
        color: #721c24;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-running {
        background: #fff3cd;
        color: #856404;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #999;
        padding: 2rem 0 1rem 0;
        font-size: 0.85rem;
        border-top: 1px solid #eee;
        margin-top: 2rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
def initialize_session_state():
    """Initialize all session state variables."""
    defaults = {
        "agent": None,
        "test_history": [],
        "is_running": False,
        "current_result": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar():
    """Render the sidebar configuration panel."""
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")

        # Provider selection
        provider = st.selectbox(
            "LLM Provider",
            options=["openai", "groq", "azure_openai"],
            index=1,
            help="Select the LLM provider for code generation.",
        )

        # Provider-specific defaults
        model_defaults = {
            "openai": "gpt-4o-mini",
            "groq": "llama-3.3-70b-versatile",
            "azure_openai": "gpt-4",
        }
        key_env_map = {
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "azure_openai": "AZURE_OPENAI_API_KEY",
        }

        # API Key
        env_key = key_env_map[provider]
        api_key = st.text_input(
            "API Key",
            type="password",
            value=os.getenv(env_key, ""),
            help=f"Your {provider.upper()} API key (reads from {env_key} env var)",
        )

        # Model name
        model_name = st.text_input(
            "Model Name",
            value=model_defaults[provider],
            help="Model identifier for the chosen provider",
        )

        # Temperature
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1,
            help="Lower = more deterministic code generation",
        )

        # Azure-specific fields
        azure_kwargs = {}
        if provider == "azure_openai":
            azure_kwargs["deployment_name"] = st.text_input(
                "Deployment Name",
                value=os.getenv("AZURE_OPENAI_LLM_MODEL_DEPLOYMENT", ""),
            )
            azure_kwargs["azure_endpoint"] = st.text_input(
                "Azure Endpoint",
                value=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            )

        # Initialize button
        if st.button("🚀 Initialize Agent", type="primary", use_container_width=True):
            if not api_key:
                st.error("Please enter your API key!")
            else:
                with st.spinner("Initializing agent..."):
                    try:
                        from backend import E2ETestingAgent

                        st.session_state.agent = E2ETestingAgent(
                            provider=provider,
                            model_name=model_name,
                            temperature=temperature,
                            api_key=api_key,
                            **azure_kwargs,
                        )
                        st.success("✅ Agent initialized!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        st.divider()

        # Workflow graph
        st.markdown("### 📊 Workflow Graph")
        if st.session_state.agent:
            try:
                with st.spinner("Loading graph..."):
                    graph_image = st.session_state.agent.get_graph_image()
                    st.image(graph_image, caption="LangGraph Workflow", use_container_width=True)
            except Exception:
                st.info("Graph visualization unavailable")
        else:
            st.info("Initialize the agent to see the workflow")

        st.divider()

        # Test history count
        st.markdown("### 📜 History")
        count = len(st.session_state.test_history)
        st.metric("Tests Run", count)


# ---------------------------------------------------------------------------
# Main Content
# ---------------------------------------------------------------------------
def render_main():
    """Render the main content area."""

    # Hero header
    st.markdown(
        """
    <div class="hero-header">
        <h1>🧪 E2E Testing Agent</h1>
        <p class="hero-subtitle">
            Describe your test in plain English — the agent writes &amp; runs
            Playwright E2E tests automatically.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if not st.session_state.agent:
        render_onboarding()
    else:
        render_test_form()

    render_footer()


def render_onboarding():
    """Show onboarding instructions when agent is not initialized."""
    st.warning("⚠️ Please initialize the agent using the sidebar configuration.")

    st.markdown("### 🎯 How It Works")
    cols = st.columns(5)
    steps = [
        ("1️⃣", "Describe Test", "Write what you want to test in plain English"),
        ("2️⃣", "Parse Actions", "Agent breaks description into atomic steps"),
        ("3️⃣", "Generate Code", "Playwright code is generated for each step"),
        ("4️⃣", "Execute Test", "Test runs against your target website"),
        ("5️⃣", "Get Report", "Detailed pass/fail report with full script"),
    ]
    for col, (emoji, title, desc) in zip(cols, steps):
        with col:
            st.markdown(
                f"""
            <div class="metric-card">
                <div style="font-size:1.8rem">{emoji}</div>
                <div class="label" style="margin-top:0.5rem">{title}</div>
                <div style="font-size:0.8rem;color:#666;margin-top:0.3rem">{desc}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("### 📝 Example Test Descriptions")

    col1, col2 = st.columns(2)
    with col1:
        st.info(
            "**Registration Form**\n\n"
            "*Test a registration form that contains username, password and "
            "password confirmation fields. After submitting it, verify that "
            "registration was successful.*"
        )
    with col2:
        st.info(
            "**Login Flow**\n\n"
            "*Test the login flow by entering valid credentials into the "
            "email and password fields, clicking Login, and verifying "
            "the dashboard loads.*"
        )


def render_test_form():
    """Render the test configuration and execution form."""
    st.markdown("### 🎯 Configure Your Test")

    col1, col2 = st.columns([3, 1])

    with col1:
        target_url = st.text_input(
            "Target URL",
            value="http://localhost:5050",
            placeholder="https://example.com",
            help="URL of the website to test. Start the demo app with: python demo_app.py",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        demo_hint = st.checkbox("Using demo app?", value=True, help="Check if testing against the built-in demo Flask app")

    query = st.text_area(
        "Test Description",
        height=120,
        placeholder=(
            "Describe what you want to test in plain English...\n\n"
            "Example: Test a registration form that contains username, password "
            "and password confirmation fields. After submitting it, verify that "
            "registration was successful."
        ),
        help="The agent will convert this into Playwright E2E test code",
    )

    col_run, col_clear, col_space = st.columns([1, 1, 4])

    with col_run:
        run_button = st.button(
            "🚀 Run E2E Test",
            type="primary",
            disabled=st.session_state.is_running,
            use_container_width=True,
        )

    with col_clear:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.current_result = None
            st.rerun()

    # Execute test
    if run_button and query and target_url:
        run_test(query, target_url)
    elif run_button and not query:
        st.warning("⚠️ Please enter a test description.")
    elif run_button and not target_url:
        st.warning("⚠️ Please enter a target URL.")

    # Display results
    if st.session_state.current_result:
        render_results(st.session_state.current_result)

    # History
    if st.session_state.test_history:
        render_history()


def run_test(query: str, target_url: str):
    """Execute the E2E test with progress tracking."""
    st.session_state.is_running = True

    progress_container = st.container()

    with progress_container:
        status = st.status("🚀 Running E2E Test...", expanded=True)

        with status:
            # Progress steps
            steps_display = {
                "parse_actions": "📋 Converting instructions to actions...",
                "parse_actions_done": None,  # dynamic
                "initial_action": "🔧 Initializing Playwright script...",
                "get_dom": None,  # dynamic
                "generate_code": None,  # dynamic
                "validate": None,  # dynamic
                "post_process": "📦 Wrapping into pytest function...",
                "execute": "▶️ Executing test with pytest...",
                "report": "📊 Generating test report...",
                "error": None,  # dynamic
                "done": None,  # dynamic
            }

            progress_log = []

            def progress_callback(step, detail):
                msg = steps_display.get(step, detail) or detail
                progress_log.append(msg)
                st.write(msg)

            st.session_state.agent.set_progress_callback(progress_callback)

            try:
                result = st.session_state.agent.run_test(query, target_url)
                st.session_state.current_result = result
                st.session_state.test_history.append(
                    {
                        "query": query,
                        "target_url": target_url,
                        "result": result,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

                # Determine status
                raw_output = result.get("test_evaluation_output", "")
                if (
                    "passed" in raw_output.lower()
                    and "failed" not in raw_output.lower()
                ):
                    status.update(label="✅ Test Passed!", state="complete")
                elif result.get("report", "").startswith("\n# ❌"):
                    status.update(label="❌ Test Failed", state="error")
                else:
                    status.update(
                        label="⚠️ Test Completed (check results)", state="complete"
                    )

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                status.update(label="❌ Error occurred", state="error")
            finally:
                st.session_state.is_running = False
                st.session_state.agent.set_progress_callback(None)


def render_results(result: dict):
    """Render the test results section."""
    st.divider()
    st.markdown("### 📊 Test Results")

    # Metric cards
    col1, col2, col3 = st.columns(3)

    test_name = result.get("test_name", "unknown")
    actions = result.get("actions", [])
    raw_output = result.get("test_evaluation_output", "")

    if "passed" in raw_output.lower() and "failed" not in raw_output.lower():
        status_badge = '<span class="badge-pass">✅ PASSED</span>'
    elif "failed" in raw_output.lower() or "error" in raw_output.lower():
        status_badge = '<span class="badge-fail">❌ FAILED</span>'
    else:
        status_badge = '<span class="badge-running">⚠️ UNKNOWN</span>'

    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="label">Test Name</div>
            <div class="value" style="font-size:0.95rem">{test_name}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="label">Status</div>
            <div class="value">{status_badge}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="label">Actions</div>
            <div class="value">{len(actions)}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("")

    # Actions taken
    with st.expander("📋 Actions Identified", expanded=True):
        for i, action in enumerate(actions):
            st.markdown(
                f'<div class="action-item"><strong>Step {i + 1}:</strong> {action}</div>',
                unsafe_allow_html=True,
            )

    # Generated script
    with st.expander("🧾 Generated Playwright Script", expanded=False):
        script = result.get("script", "No script generated")
        st.code(script, language="python", line_numbers=True)

    # Test output
    with st.expander("📟 Test Execution Output", expanded=False):
        st.code(raw_output or "No output captured", language="text")

    # Full report
    with st.expander("📊 Full Report (Markdown)", expanded=False):
        report = result.get("report", "No report generated")
        st.markdown(report)


def render_history():
    """Render the test history section."""
    st.divider()
    st.markdown("### 📜 Test History")

    with st.expander(
        f"View History ({len(st.session_state.test_history)} tests)", expanded=False
    ):
        for idx, item in enumerate(reversed(st.session_state.test_history)):
            num = len(st.session_state.test_history) - idx
            raw = item["result"].get("test_evaluation_output", "")
            if "passed" in raw.lower() and "failed" not in raw.lower():
                badge = "✅"
            elif "failed" in raw.lower():
                badge = "❌"
            else:
                badge = "⚠️"

            st.markdown(
                f"**{badge} Test {num}** — `{item['target_url']}` — "
                f"*{item['timestamp']}*"
            )
            st.caption(item["query"][:120] + ("..." if len(item["query"]) > 120 else ""))
            st.markdown("---")


def render_footer():
    """Render the page footer."""
    st.markdown(
        """
    <div class="footer">
        <p>Built with <strong>LangGraph</strong>, <strong>Playwright</strong>,
        and <strong>Streamlit</strong> &nbsp;|&nbsp;
        Powered by <strong>OpenAI</strong> &nbsp;|&nbsp;
        Part of <a href="https://github.com/ayusingh-54/agent-forge"
        target="_blank">Agent Forge</a></p>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main():
    """Main application entry point."""
    initialize_session_state()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
