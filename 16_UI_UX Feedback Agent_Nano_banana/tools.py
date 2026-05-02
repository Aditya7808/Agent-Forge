"""Tools for the UI/UX Feedback Agent Team.

Includes:
- edit_landing_page_image — refine an existing design
- generate_improved_landing_page — create a new improved design
- list_versions — show version history of all assets
- compare_versions — produce a visual diff narrative between two versions
- export_design_report — write a markdown report of the session
- estimate_color_contrast — WCAG contrast ratio between two hex colors
"""

from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")

from google import genai
from google.genai import types
from google.adk.tools import ToolContext
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Where exported reports land. Override with REPORTS_DIR env var.
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "./reports")).resolve()


# ============================================================================
# Asset version helpers
# ============================================================================

def get_next_version_number(tool_context: ToolContext, asset_name: str) -> int:
    asset_versions = tool_context.state.get("asset_versions", {})
    return asset_versions.get(asset_name, 0) + 1


def update_asset_version(
    tool_context: ToolContext, asset_name: str, version: int, filename: str
) -> None:
    state = tool_context.state
    state.setdefault("asset_versions", {})[asset_name] = version
    state.setdefault("asset_filenames", {})[asset_name] = filename

    # Append to a version log so we can show history later
    history = state.setdefault("asset_history", [])
    history.append(
        {
            "asset_name": asset_name,
            "version": version,
            "filename": filename,
            "timestamp": _now_iso(),
        }
    )


def create_versioned_filename(asset_name: str, version: int, ext: str = "png") -> str:
    return f"{asset_name}_v{version}.{ext}"


async def load_landing_page_image(tool_context: ToolContext, filename: str):
    try:
        part = await tool_context.load_artifact(filename)
        if part:
            logger.info("Loaded artifact %s", filename)
            return part
        logger.warning("Artifact not found: %s", filename)
        return None
    except Exception as exc:
        logger.error("Error loading artifact %s: %s", filename, exc)
        return None


# ============================================================================
# Pydantic input models
# ============================================================================

class EditLandingPageInput(BaseModel):
    artifact_filename: str = Field(..., description="Filename of the landing page artifact to edit.")
    prompt: str = Field(..., description="Detailed description of UI/UX improvements to apply.")
    asset_name: Optional[str] = Field(default=None, description="Optional asset name for the new version.")


class GenerateImprovedLandingPageInput(BaseModel):
    prompt: str = Field(..., description="Detailed description of the improved landing page.")
    aspect_ratio: str = Field(default="16:9", description="Desired aspect ratio. Default 16:9.")
    asset_name: str = Field(default="landing_page_improved", description="Base name for the design.")
    reference_image: Optional[str] = Field(default=None, description="Optional reference artifact filename.")


class CompareVersionsInput(BaseModel):
    asset_name: str = Field(..., description="Asset family to compare.")
    version_a: int = Field(..., description="Older version number.")
    version_b: int = Field(..., description="Newer version number.")


class ExportReportInput(BaseModel):
    title: str = Field(default="UI_UX Feedback Report", description="Report title.")
    include_history: bool = Field(default=True, description="Include the full version history.")


class ContrastInput(BaseModel):
    foreground_hex: str = Field(..., description="Foreground color, e.g. '#0A2540' or '0A2540'.")
    background_hex: str = Field(..., description="Background color, e.g. '#FFFFFF' or 'FFFFFF'.")
    text_size: str = Field(default="body", description="One of: 'body', 'large' (24px+), 'ui' (UI components).")


# ============================================================================
# Image editing tool
# ============================================================================

UI_UX_BEST_PRACTICES = """
**Apply these UI/UX best practices while editing:**
- Maintain visual hierarchy (size, color, spacing)
- Ensure sufficient whitespace for breathing room
- Use a consistent alignment and grid system
- Make CTAs prominent with contrasting colors
- Improve readability (font size, line height, contrast)
- Follow modern web design principles
- Keep the overall brand aesthetic
"""


def _require_api_key() -> None:
    if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" not in os.environ:
        raise ValueError(
            "Set GEMINI_API_KEY or GOOGLE_API_KEY in your environment or .env file."
        )


async def edit_landing_page_image(
    tool_context: ToolContext, inputs: EditLandingPageInput
) -> str:
    """Edit a landing page image to apply UI/UX improvements."""
    _require_api_key()
    logger.info("Editing landing page image")

    try:
        client = genai.Client()
        inputs = EditLandingPageInput(**inputs) if isinstance(inputs, dict) else inputs

        loaded = await tool_context.load_artifact(inputs.artifact_filename)
        if not loaded:
            return f"❌ Could not find artifact: {inputs.artifact_filename}"

        enhanced_prompt = f"{inputs.prompt}\n\n{UI_UX_BEST_PRACTICES}\nMake improvements look natural and professional."
        contents = [
            types.Content(
                role="user",
                parts=[loaded, types.Part.from_text(text=enhanced_prompt)],
            )
        ]
        config = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])

        # Determine asset name and versioned filename
        if inputs.asset_name:
            asset_name = inputs.asset_name
        else:
            asset_name = (
                tool_context.state.get("current_asset_name")
                or (
                    inputs.artifact_filename.split("_v")[0]
                    if "_v" in inputs.artifact_filename
                    else "landing_page"
                )
            )
        version = get_next_version_number(tool_context, asset_name)
        edited_filename = create_versioned_filename(asset_name, version)

        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash-image", contents=contents, config=config
        ):
            cands = getattr(chunk, "candidates", None)
            if not cands or not cands[0].content or not cands[0].content.parts:
                continue
            part = cands[0].content.parts[0]
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                edited_part = types.Part(inline_data=inline)
                saved_version = await tool_context.save_artifact(
                    filename=edited_filename, artifact=edited_part
                )
                update_asset_version(tool_context, asset_name, saved_version, edited_filename)
                tool_context.state["last_edited_landing_page"] = edited_filename
                tool_context.state["current_asset_name"] = asset_name
                logger.info("Saved edit %s (v%s)", edited_filename, saved_version)
                return (
                    f"✅ **Landing page edited!**\n\n"
                    f"Saved as: **{edited_filename}** (v{saved_version} of `{asset_name}`)\n\n"
                    f"_Tip: ask me to compare v{max(saved_version-1, 1)} ↔ v{saved_version} to see what changed._"
                )

        return "No edited landing page was generated. Please try again with a more specific prompt."

    except Exception as exc:
        logger.exception("edit_landing_page_image failed")
        return f"An error occurred while editing the landing page: {exc}"


# ============================================================================
# Generate improved landing page
# ============================================================================

DESIGN_REQUIREMENTS = """
**Design Requirements:**
- Modern, clean aesthetic
- Clear visual hierarchy
- Prominent, well-designed CTAs
- Proper whitespace and breathing room
- Professional typography with clear hierarchy
- Accessible color contrast (WCAG AA)
- Mobile-first responsive considerations
- Photorealistic UI mockup, Figma-quality, 4K rendering
"""


async def generate_improved_landing_page(
    tool_context: ToolContext, inputs: GenerateImprovedLandingPageInput
) -> str:
    """Generate an improved landing page design from a prompt."""
    _require_api_key()
    logger.info("Generating improved landing page")

    try:
        client = genai.Client()
        inputs = (
            GenerateImprovedLandingPageInput(**inputs)
            if isinstance(inputs, dict)
            else inputs
        )

        reference_part = None
        if inputs.reference_image:
            reference_part = await load_landing_page_image(tool_context, inputs.reference_image)

        latest_analysis = tool_context.state.get("latest_analysis", "")
        latest_strategy = tool_context.state.get("latest_strategy", "")

        enhancement_prompt = f"""
Create a professional landing page design that incorporates these improvements:

{inputs.prompt}

**Design Strategist Spec:**
{latest_strategy[:1500] if latest_strategy else "(no spec available)"}

**Critic Insights:**
{latest_analysis[:800] if latest_analysis else "(no analysis available)"}

{DESIGN_REQUIREMENTS}

Aspect ratio: {inputs.aspect_ratio}
Create a magazine-quality UI/UX design.
"""

        # Have a fast model rewrite the prompt to maximum descriptiveness first
        rewritten = client.models.generate_content(
            model="gemini-2.5-flash", contents=enhancement_prompt
        ).text

        parts = [types.Part.from_text(text=rewritten)]
        if reference_part:
            parts.append(reference_part)
        contents = [types.Content(role="user", parts=parts)]
        config = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])

        version = get_next_version_number(tool_context, inputs.asset_name)
        artifact_filename = create_versioned_filename(inputs.asset_name, version)

        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash-image", contents=contents, config=config
        ):
            cands = getattr(chunk, "candidates", None)
            if not cands or not cands[0].content or not cands[0].content.parts:
                continue
            part = cands[0].content.parts[0]
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                image_part = types.Part(inline_data=inline)
                saved_version = await tool_context.save_artifact(
                    filename=artifact_filename, artifact=image_part
                )
                update_asset_version(
                    tool_context, inputs.asset_name, saved_version, artifact_filename
                )
                tool_context.state["last_generated_landing_page"] = artifact_filename
                tool_context.state["current_asset_name"] = inputs.asset_name
                logger.info("Saved %s (v%s)", artifact_filename, saved_version)
                return (
                    f"✅ **Improved landing page generated!**\n\n"
                    f"Saved as: **{artifact_filename}** (v{saved_version} of `{inputs.asset_name}`)\n\n"
                    f"_Try next: refine with `make the CTA orange` or `add testimonials section`._"
                )

        return "No improved landing page was generated. Please retry with a more detailed prompt."

    except Exception as exc:
        logger.exception("generate_improved_landing_page failed")
        return f"An error occurred while generating the landing page: {exc}"


# ============================================================================
# Version listing
# ============================================================================

def list_versions(tool_context: ToolContext) -> str:
    """Return a markdown table of all asset versions in the current session."""
    history = tool_context.state.get("asset_history", [])
    if not history:
        return "_No designs generated yet. Upload a screenshot or ask for a redesign to start._"

    lines = ["| # | Asset | Version | Filename | Created |", "|---|-------|---------|----------|---------|"]
    for i, h in enumerate(history, 1):
        lines.append(
            f"| {i} | `{h['asset_name']}` | v{h['version']} | `{h['filename']}` | {h['timestamp']} |"
        )
    current = tool_context.state.get("current_asset_name")
    footer = f"\n_Currently active asset: `{current}`_" if current else ""
    return "### 🗂️ Version History\n\n" + "\n".join(lines) + footer


# ============================================================================
# Compare versions — narrative diff
# ============================================================================

async def compare_versions(
    tool_context: ToolContext, inputs: CompareVersionsInput
) -> str:
    """Compare two versions of an asset by loading both and asking a vision
    model to narrate the differences."""
    _require_api_key()

    inputs = CompareVersionsInput(**inputs) if isinstance(inputs, dict) else inputs

    file_a = create_versioned_filename(inputs.asset_name, inputs.version_a)
    file_b = create_versioned_filename(inputs.asset_name, inputs.version_b)

    part_a = await load_landing_page_image(tool_context, file_a)
    part_b = await load_landing_page_image(tool_context, file_b)
    if not part_a or not part_b:
        missing = []
        if not part_a:
            missing.append(file_a)
        if not part_b:
            missing.append(file_b)
        return f"❌ Could not load: {', '.join(missing)}"

    prompt = f"""You are a design critic. Two versions of the same landing page are
attached. Image A is **v{inputs.version_a}** (older). Image B is **v{inputs.version_b}** (newer).

Produce a markdown comparison:

### 🔍 What Changed
Bulleted list of every visual difference you can spot. Be specific:
section, element, before → after.

### 📊 Side-by-Side Scorecard
| Dimension | v{inputs.version_a} | v{inputs.version_b} | Winner |
|-----------|---------------------|---------------------|--------|
| Visual hierarchy | ... | ... | ... |
| Typography | ... | ... | ... |
| Color & contrast | ... | ... | ... |
| CTA prominence | ... | ... | ... |
| Trust & polish | ... | ... | ... |

### 🏆 Verdict
One paragraph: which version is stronger and why? What would you keep,
what would you revert?
"""

    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(
                role="user",
                parts=[part_a, part_b, types.Part.from_text(text=prompt)],
            )
        ],
    )
    return response.text or "No comparison was returned."


# ============================================================================
# Export design report
# ============================================================================

def export_design_report(tool_context: ToolContext, inputs: ExportReportInput) -> str:
    """Write a markdown report of the current session to disk."""
    inputs = ExportReportInput(**inputs) if isinstance(inputs, dict) else inputs
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    state = tool_context.state
    timestamp = _now_compact()
    safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in inputs.title)
    report_path = REPORTS_DIR / f"{safe_title}_{timestamp}.md"

    sections = [
        f"# {inputs.title}",
        f"_Generated {_now_iso()}_",
        "",
        "## 🎨 Critic Analysis",
        state.get("latest_analysis", "_No analysis recorded._"),
        "",
        "## 📐 Design Strategy",
        state.get("latest_strategy", "_No strategy recorded._"),
        "",
        "## 🖼️ Generated Assets",
        f"- **Latest generated:** `{state.get('last_generated_landing_page', '—')}`",
        f"- **Latest edited:** `{state.get('last_edited_landing_page', '—')}`",
        f"- **Active asset:** `{state.get('current_asset_name', '—')}`",
    ]

    if inputs.include_history:
        history = state.get("asset_history", [])
        if history:
            sections += ["", "## 🗂️ Version History"]
            for h in history:
                sections.append(
                    f"- `{h['filename']}` — `{h['asset_name']}` v{h['version']} ({h['timestamp']})"
                )

    report_path.write_text("\n".join(sections), encoding="utf-8")
    logger.info("Exported report to %s", report_path)
    return f"📄 Report exported to `{report_path}`"


# ============================================================================
# Color contrast estimator (WCAG)
# ============================================================================

def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        raise ValueError(f"Invalid hex color: {value!r}")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def _channel(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (_channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def estimate_color_contrast(inputs: ContrastInput) -> str:
    """Compute WCAG contrast ratio between two colors and return a verdict."""
    inputs = ContrastInput(**inputs) if isinstance(inputs, dict) else inputs

    try:
        fg = _hex_to_rgb(inputs.foreground_hex)
        bg = _hex_to_rgb(inputs.background_hex)
    except ValueError as exc:
        return f"❌ {exc}"

    l1, l2 = _relative_luminance(fg), _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    ratio = (lighter + 0.05) / (darker + 0.05)

    thresholds = {
        "body": (4.5, 7.0, "body text"),
        "large": (3.0, 4.5, "large text (24px+ or 18.66px bold)"),
        "ui": (3.0, 3.0, "UI components and graphical objects"),
    }
    aa_threshold, aaa_threshold, label = thresholds.get(
        inputs.text_size.lower(), thresholds["body"]
    )

    if ratio >= aaa_threshold:
        verdict = "✅ AAA — exceeds the highest WCAG bar"
    elif ratio >= aa_threshold:
        verdict = "✅ AA — meets the standard accessibility bar"
    else:
        verdict = "❌ FAIL — does not meet WCAG AA"

    return (
        f"### 🎨 Contrast Check\n\n"
        f"- **Foreground:** `{inputs.foreground_hex}`\n"
        f"- **Background:** `{inputs.background_hex}`\n"
        f"- **Context:** {label}\n"
        f"- **Ratio:** **{ratio:.2f} : 1**\n"
        f"- **WCAG AA min:** {aa_threshold}:1 · **AAA min:** {aaa_threshold}:1\n\n"
        f"**Verdict:** {verdict}"
    )
