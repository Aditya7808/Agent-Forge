"""UI/UX Feedback Agent Team — multi-agent orchestration.

Architecture:

    coordinator (root)
        ├── info_agent              (general Q&A and onboarding)
        ├── design_editor           (iterative refinements)
        ├── accessibility_auditor   (WCAG deep-dive)
        ├── conversion_optimizer    (CRO and A/B hypotheses)
        └── analysis_pipeline       (sequential)
              ├── ui_critic         (visual analysis + scoring)
              ├── design_strategist (build-ready design spec)
              └── visual_implementer(generates redesigned image + report)
"""

from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search

from .prompts import (
    UI_CRITIC_INSTRUCTION,
    DESIGN_STRATEGIST_INSTRUCTION,
    VISUAL_IMPLEMENTER_INSTRUCTION,
    DESIGN_EDITOR_INSTRUCTION,
    INFO_AGENT_INSTRUCTION,
    ACCESSIBILITY_AUDITOR_INSTRUCTION,
    CONVERSION_OPTIMIZER_INSTRUCTION,
    COORDINATOR_INSTRUCTION,
)
from .tools import (
    edit_landing_page_image,
    generate_improved_landing_page,
    compare_versions,
    list_versions,
    export_design_report,
    estimate_color_contrast,
)

# Vision-capable model for any agent that needs to "see" the uploaded screenshot
VISION_MODEL = "gemini-2.5-flash"
# Faster model for routing/coordination where vision isn't needed
ROUTER_MODEL = "gemini-2.5-flash"


# ----------------------------------------------------------------------------
# Sequential analysis pipeline
# ----------------------------------------------------------------------------

ui_critic = Agent(
    name="ui_critic",
    model=VISION_MODEL,
    description="Senior UI/UX critic. Analyzes uploaded landing page screenshots and scores them across 8 dimensions.",
    instruction=UI_CRITIC_INSTRUCTION,
    tools=[google_search],
    output_key="latest_analysis",
)

design_strategist = Agent(
    name="design_strategist",
    model=VISION_MODEL,
    description="Principal product designer. Converts critique into a build-ready spec with design tokens and a priority matrix.",
    instruction=DESIGN_STRATEGIST_INSTRUCTION,
    tools=[google_search, estimate_color_contrast],
    output_key="latest_strategy",
)

visual_implementer = Agent(
    name="visual_implementer",
    model=VISION_MODEL,
    description="Senior visual designer. Renders the redesigned landing page mockup and produces a change log.",
    instruction=VISUAL_IMPLEMENTER_INSTRUCTION,
    tools=[generate_improved_landing_page, export_design_report],
)

analysis_pipeline = SequentialAgent(
    name="analysis_pipeline",
    description="Full critique → strategy → redesign workflow. Use when the user uploads a screenshot or asks for end-to-end feedback.",
    sub_agents=[ui_critic, design_strategist, visual_implementer],
)


# ----------------------------------------------------------------------------
# Specialist single-purpose agents
# ----------------------------------------------------------------------------

design_editor = Agent(
    name="design_editor",
    model=VISION_MODEL,
    description="Iterative refinement specialist. Use for tweaks like 'make the CTA bigger' or 'try a darker palette'.",
    instruction=DESIGN_EDITOR_INSTRUCTION,
    tools=[edit_landing_page_image, list_versions, compare_versions],
)

accessibility_auditor = Agent(
    name="accessibility_auditor",
    model=VISION_MODEL,
    description="WCAG 2.2 accessibility specialist. Audits contrast, focus, touch targets, and semantic structure.",
    instruction=ACCESSIBILITY_AUDITOR_INSTRUCTION,
    tools=[estimate_color_contrast, google_search],
)

conversion_optimizer = Agent(
    name="conversion_optimizer",
    model=VISION_MODEL,
    description="CRO specialist. Audits funnel, generates A/B test hypotheses, estimates conversion lift.",
    instruction=CONVERSION_OPTIMIZER_INSTRUCTION,
    tools=[google_search],
)

info_agent = Agent(
    name="info_agent",
    model=ROUTER_MODEL,
    description="Front desk. Handles general questions, onboarding, and 'how does this work?' style requests.",
    instruction=INFO_AGENT_INSTRUCTION,
)


# ----------------------------------------------------------------------------
# Coordinator (root)
# ----------------------------------------------------------------------------

root_agent = Agent(
    name="coordinator",
    model=ROUTER_MODEL,
    description="Coordinator for the UI/UX Feedback Team. Routes user intent to the right specialist.",
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[
        info_agent,
        analysis_pipeline,
        design_editor,
        accessibility_auditor,
        conversion_optimizer,
    ],
)
