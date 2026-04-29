"""Gemini-powered personalized summary grounded in s(CASP) outputs.

Gemini is allowed to rephrase already-computed structured outputs into a
warm, personalized explanation. It must NOT introduce new requirements,
override the rules engine, or hallucinate documents/exams. A
deterministic fallback covers cases where Gemini is disabled, unreachable,
or returns invalid output.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any

from .gemini_parser import env_bool
from .models import DocumentSelections, FactState, PolicyResult
from .report_composer import Report


@dataclass
class GeminiSummaryConfig:
    """Configuration for the optional summary generator."""

    enabled: bool = False
    api_key: str | None = None
    model: str | None = None

    @classmethod
    def from_env(cls, enabled: bool | None = None) -> "GeminiSummaryConfig":
        return cls(
            enabled=env_bool("ENABLE_GEMINI_SUMMARY", False) if enabled is None else enabled,
            api_key=os.getenv("GEMINI_API_KEY"),
            model=os.getenv("GEMINI_MODEL"),
        )


def generate_summary(
    facts: FactState,
    result: PolicyResult,
    documents: DocumentSelections,
    report: Report,
    config: GeminiSummaryConfig | None = None,
    client: Any | None = None,
) -> str:
    """Return a personalized summary, using Gemini if configured."""

    deterministic = build_deterministic_summary(facts, result, report)
    active_config = config or GeminiSummaryConfig.from_env()
    if not active_config.enabled or result.error:
        return deterministic
    try:
        polished = call_gemini(facts, result, documents, report, active_config, client=client)
        return polished or deterministic
    except Exception:
        return deterministic


def build_deterministic_summary(facts: FactState, result: PolicyResult, report: Report) -> str:
    """Compose a grounded fallback summary when Gemini is unavailable."""

    if result.error:
        return (
            "The rules engine could not run. Please install s(CASP) and verify "
            "with `scasp --version`, then retry. The rest of the report uses "
            "your stored answers only."
        )

    paragraphs: list[str] = []
    intro_parts: list[str] = []
    intro_parts.append(report.case_outcome)
    if report.service_method:
        intro_parts.append(f"The likely service method is **{report.service_method}**.")
    paragraphs.append(" ".join(intro_parts))

    confirmation_parts: list[str] = []
    if facts.age is not None:
        confirmation_parts.append(f"You provided your age as {facts.age}.")
    if facts.has_out_of_state_license is True and facts.out_of_state_license_unexpired is True:
        confirmation_parts.append("Your out-of-state license is valid and unexpired.")
    if facts.has_identity_doc is True:
        confirmation_parts.append("Identity documents are confirmed.")
    if facts.has_social_security is True:
        confirmation_parts.append("Social Security proof is confirmed.")
    if facts.has_texas_residency_docs is True:
        confirmation_parts.append("Texas residency documents are confirmed.")
    if confirmation_parts:
        paragraphs.append(" ".join(confirmation_parts))

    next_step_lines: list[str] = []
    if report.missing_items:
        missing = ", ".join(report.missing_items)
        next_step_lines.append(f"Items still unclear: {missing}.")
    if report.next_steps:
        next_step_lines.append(report.next_steps[0])
    if next_step_lines:
        paragraphs.append(" ".join(next_step_lines))

    return "\n\n".join(paragraphs)


def call_gemini(
    facts: FactState,
    result: PolicyResult,
    documents: DocumentSelections,
    report: Report,
    config: GeminiSummaryConfig,
    client: Any | None = None,
) -> str:
    """Invoke Gemini for the personalized summary."""

    if not config.api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    if not config.model:
        raise RuntimeError("GEMINI_MODEL is not set")

    active_client = client or _create_client(config.api_key)
    response = active_client.models.generate_content(
        model=config.model,
        contents=_build_prompt(facts, result, documents, report),
        config={"temperature": 0.2},
    )
    text = getattr(response, "text", "") or ""
    return text.strip()


def _create_client(api_key: str) -> Any:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai is not installed") from exc
    return genai.Client(api_key=api_key)


def _build_prompt(
    facts: FactState,
    result: PolicyResult,
    documents: DocumentSelections,
    report: Report,
) -> str:
    payload = {
        "facts": _public_facts(facts),
        "documents": {
            "selected": documents.selected,
            "other_text": documents.other_text,
            "unsure": documents.unsure,
            "none": documents.none,
            "lawful_presence_choice": documents.lawful_presence_choice,
        },
        "result": _public_result(result),
        "report": {
            "case_label": report.case_label,
            "case_outcome": report.case_outcome,
            "service_method": report.service_method,
            "summary_lines": report.summary_lines,
            "why_lines": report.why_lines,
            "missing_items": report.missing_items,
            "next_steps": report.next_steps,
            "fact_summary": report.fact_summary,
            "sections": [
                {
                    "title": section.title,
                    "items": [
                        {"label": item.label, "status": item.status, "detail": item.detail}
                        for item in section.items
                    ],
                }
                for section in report.sections
            ],
        },
    }
    return (
        "You are writing a personalized 2-paragraph summary for a Texas driver "
        "license guidance assistant. The reasoning engine s(CASP) is the source "
        "of truth; you must NOT add, remove, or change any required document, "
        "exam, waiver, missing item, service mode, or next step. Only rephrase "
        "what is provided in the structured payload below.\n\n"
        "Rules:\n"
        "- Use a warm, direct, second-person tone (\"you\").\n"
        "- Paragraph 1: confirm the user's case and key facts.\n"
        "- Paragraph 2: explain what they still need to do, grounded only in the data below.\n"
        "- Never invent documents, deadlines, fees, or eligibility rules.\n"
        "- If a field is unknown or missing, say so plainly instead of guessing.\n"
        "- Do not include disclaimers or markdown headings.\n"
        "- Keep it concise: roughly 80 to 140 words total.\n\n"
        f"Structured payload:\n{json.dumps(payload, default=str, indent=2)}"
    )


def _public_facts(facts: FactState) -> dict[str, Any]:
    return facts.to_public_dict()


def _public_result(result: PolicyResult) -> dict[str, Any]:
    data = asdict(result)
    data.pop("raw", None)
    return data
