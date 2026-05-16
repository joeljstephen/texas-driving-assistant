"""Streamlit UI for the Texas Driver License Guidance Assistant."""

from __future__ import annotations

from dataclasses import replace
from html import escape
import os
from pathlib import Path
import time
from typing import Any

import streamlit as st

from backend.case_detection import CASE_INTROS, case_label, detect_case
from backend.document_catalog import DOCUMENT_CATEGORIES, option_label
from backend.followup import FollowUpConfig, answer_follow_up
from backend.followup_state import reconcile_followup_documents, should_apply_followup_facts
from backend.gemini_parser import GeminiParserConfig, env_bool, load_dotenv_file, parse_with_gemini_or_fallback
from backend.gemini_summary import GeminiSummaryConfig, generate_summary
from backend.intake import (
    IntakeField,
    IntakeStep,
    SCENARIOS,
    apply_document_selections,
    facts_from_intake,
    intake_defaults,
    steps_for,
)
from backend.models import AssistantSession, ChatMessage, DocumentSelections, FactState
from backend.report_composer import ChecklistItem, Report, ReportSection, compose_report
from backend.scasp_runner import ScaspRunner, run_policy_safely
from backend.scenarios import QUICK_ACTIONS
from backend.state_manager import append_assistant_turn, merge_facts, reset_session


st.set_page_config(
    page_title="Texas Driver License Guidance Assistant",
    layout="wide",
)
load_dotenv_file()


STYLE_PATH = Path(__file__).with_name("styles.css")


SCENARIO_KEY_FROM_QUICK_ACTION = {
    "First-time application": "first_time",
    "Moving to Texas with out-of-state license": "transfer",
    "Renew license": "renewal",
    "Replace lost license": "replacement",
}


def inject_styles() -> None:
    styles = STYLE_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(
        """
        <div class="app-kicker">Texas Driver License Guidance Assistant</div>
        <h1 class="app-title">A guided assistant for Texas driver license cases</h1>
        <div class="app-subtitle">
            Describe your situation in plain English. The assistant identifies the case, walks you through
            a short guided intake, and then runs the s(CASP) rule engine once to produce a personalized
            structured report.
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_session() -> AssistantSession:
    if "assistant_session" not in st.session_state:
        st.session_state.assistant_session = reset_session()
    return st.session_state.assistant_session


def reset_all_state() -> None:
    st.session_state.assistant_session = reset_session()
    st.session_state.pop("intake_form_state", None)
    st.session_state.pop("followup_messages", None)
    st.session_state.pop("report_summary", None)


def settings_block() -> dict[str, bool]:
    gemini_available = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "parser": gemini_available and env_bool("ENABLE_GEMINI_PARSER", True),
        "summary": gemini_available and env_bool("ENABLE_GEMINI_SUMMARY", False),
        "followup": gemini_available and env_bool("ENABLE_GEMINI_FOLLOWUP", False),
    }


def render_status_row(session: AssistantSession) -> None:
    parser = session.last_parse_result.source if session.last_parse_result else "not run"
    detected = case_label(session.detected_case)
    runs = "Done" if session.last_policy_result else "Pending"
    missing = len(session.last_policy_result.missing_info) if session.last_policy_result else 0
    st.markdown(
        f"""
        <div class="status-row">
            <span class="status-pill">Parser: {parser}</span>
            <span class="status-pill">Detected case: {escape(detected)}</span>
            <span class="status-pill">s(CASP) run: {runs}</span>
            <span class="status-pill">Missing items: {missing}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------- Step 1: chat-style entry -----------------


def render_entry(session: AssistantSession, settings: dict[str, bool]) -> None:
    st.subheader("Describe your situation")
    st.caption(
        "Type a quick message about what you're trying to do. Examples below show "
        "what works well."
    )

    if session.messages:
        with st.container():
            for message in session.messages[-4:]:
                with st.chat_message(message.role):
                    st.markdown(message.content)

    prompt = st.chat_input(
        "Example: I moved to Texas with an Oklahoma license",
        key="entry_chat_input",
    )
    if prompt:
        run_case_detection(prompt, settings)
        st.rerun()

    st.markdown("##### Common starting points")
    quick_items = list(QUICK_ACTIONS.items())
    for row_start in range(0, len(quick_items), 2):
        cols = st.columns(2)
        for col, (label, prompt_text) in zip(cols, quick_items[row_start : row_start + 2]):
            scenario_key = SCENARIO_KEY_FROM_QUICK_ACTION.get(label)
            scenario = SCENARIOS.get(scenario_key) if scenario_key else None
            description = scenario.description if scenario else ""
            with col:
                with st.container(border=True, key=f"quick_option_{scenario_key or label}"):
                    st.markdown(
                        f"""
                        <div class="quick-title">{escape(label)}</div>
                        <p class="quick-copy">{escape(description)}</p>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("Start", key=f"quick_{label}", use_container_width=True):
                        run_case_detection(prompt_text, settings)
                        st.rerun()
        if row_start + 2 < len(quick_items):
            st.markdown('<div class="quick-row-gap"></div>', unsafe_allow_html=True)


def run_case_detection(user_text: str, settings: dict[str, bool]) -> None:
    session = get_session()
    detection = detect_case(user_text, use_gemini=settings["parser"], current_facts=session.facts)
    session.messages.append(ChatMessage(role="user", content=user_text))
    session.facts = merge_facts(session.facts, detection.facts, allow_overwrite=True)
    session.last_parse_result = detection.parse_result
    session.last_policy_result = None
    session.detected_case = detection.scenario_key
    session.detection_message = detection.message
    session.intake_step = 0
    session.messages.append(ChatMessage(role="assistant", content=detection.message))
    st.session_state.assistant_session = session
    st.session_state.pop("intake_form_state", None)
    st.session_state.pop("report_summary", None)


# ----------------- Step 2: guided intake -----------------


def render_intake(session: AssistantSession, settings: dict[str, bool]) -> None:
    scenario_key = session.detected_case
    if not scenario_key:
        return

    scenario = SCENARIOS[scenario_key]
    steps = steps_for(scenario_key)
    total = len(steps)
    current_index = max(0, min(session.intake_step, total - 1))

    render_detection_card(session)
    render_scenario_picker(session)

    st.markdown(f'<div class="step-title">{escape(scenario.label)} — guided intake</div>', unsafe_allow_html=True)
    pills = []
    for index, step in enumerate(steps):
        css = "step-pill"
        if index < current_index:
            css += " done"
        elif index == current_index:
            css += " active"
        pills.append(f'<span class="{css}">{index + 1}. {escape(step.title)}</span>')
    st.markdown(f'<div class="step-bar">{"".join(pills)}</div>', unsafe_allow_html=True)

    step = steps[current_index]
    render_step(session, scenario_key, step, current_index, total, settings)


def render_detection_card(session: AssistantSession) -> None:
    if not session.detected_case:
        return
    label = case_label(session.detected_case)
    intro = session.detection_message or CASE_INTROS.get(session.detected_case, "")
    st.markdown(
        f"""
        <div class="detection-card">
            <div class="label">Detected case</div>
            <div class="case">{escape(label)}</div>
            <div class="body">{escape(intro)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scenario_picker(session: AssistantSession) -> None:
    with st.expander("This isn't quite right? Pick a different scenario", expanded=False):
        labels = [scenario.label for scenario in SCENARIOS.values()]
        keys = list(SCENARIOS)
        index = keys.index(session.detected_case) if session.detected_case in keys else 0
        chosen_label = st.selectbox("Choose a scenario", labels, index=index, key="scenario_override")
        chosen_key = keys[labels.index(chosen_label)]
        if chosen_key != session.detected_case:
            session.detected_case = chosen_key
            session.facts.goal = "replacement" if chosen_key == "change_info" else chosen_key
            session.last_policy_result = None
            session.intake_step = 0
            st.session_state.pop("intake_form_state", None)
            st.session_state.assistant_session = session
            st.rerun()


def render_step(
    session: AssistantSession,
    scenario_key: str,
    step: IntakeStep,
    current_index: int,
    total: int,
    settings: dict[str, bool],
) -> None:
    st.markdown(f'<div class="step-title">{escape(step.title)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="step-description">{escape(step.description)}</div>', unsafe_allow_html=True)

    form_state = ensure_form_state(session, scenario_key)

    if step.summary_kind == "review":
        render_review_step(session, form_state)
    else:
        for field_def in step.fields:
            render_field(scenario_key, field_def, form_state)
        for category_key in step.document_categories:
            render_document_category(category_key, form_state)

    render_step_nav(session, scenario_key, current_index, total, settings)


def ensure_form_state(session: AssistantSession, scenario_key: str) -> dict[str, Any]:
    state = st.session_state.get("intake_form_state")
    if not state or state.get("scenario") != scenario_key:
        defaults = intake_defaults(scenario_key, session.facts)
        documents = session.documents
        state = {
            "scenario": scenario_key,
            "values": dict(defaults),
            "documents": {
                "selected": dict(documents.selected),
                "other_text": dict(documents.other_text),
                "unsure": dict(documents.unsure),
                "none": dict(documents.none),
                "lawful_presence_choice": documents.lawful_presence_choice or lawful_presence_choice_from_facts(session.facts),
            },
        }
        st.session_state["intake_form_state"] = state
    return state


def lawful_presence_choice_from_facts(facts: FactState) -> str | None:
    if facts.us_citizen is True:
        return "us_citizen"
    if facts.lawful_presence_category_known is True:
        return "other_lawful_presence"
    if facts.lawful_presence_category_known is False:
        return None
    return None


def render_field(scenario_key: str, field_def: IntakeField, form_state: dict[str, Any]) -> None:
    values: dict[str, Any] = form_state.setdefault("values", {})
    widget_key = f"intake_{scenario_key}_{field_def.key}"
    if field_def.helper_title and field_def.helper_text:
        with st.expander(f"ℹ️  {field_def.helper_title}", expanded=False):
            st.write(field_def.helper_text)
    if field_def.kind == "number":
        if widget_key not in st.session_state:
            st.session_state[widget_key] = int(values.get(field_def.key, 18))
        values[field_def.key] = int(
            st.number_input(
            field_def.label,
            min_value=0,
            max_value=120,
            step=1,
            key=widget_key,
            help=field_def.description or None,
        )
        )
    elif field_def.kind == "choice":
        options = field_def.options or []
        default_value = values.get(field_def.key, options[0] if options else None)
        if options:
            if widget_key not in st.session_state:
                st.session_state[widget_key] = default_value if default_value in options else options[0]
            values[field_def.key] = st.radio(
                field_def.label,
                options,
                horizontal=len(options) <= 4,
                key=widget_key,
                help=field_def.description or None,
            )


def render_document_category(category_key: str, form_state: dict[str, Any]) -> None:
    if category_key not in DOCUMENT_CATEGORIES:
        return
    category = DOCUMENT_CATEGORIES[category_key]
    documents = form_state.setdefault("documents", {})
    documents.setdefault("selected", {})
    documents.setdefault("other_text", {})
    documents.setdefault("unsure", {})
    documents.setdefault("none", {})

    with st.container(border=True):
        st.markdown(f"**{category.title}**")
        st.caption(category.summary)
        with st.expander(f"ℹ️  {category.helper_title}", expanded=False):
            st.write(category.helper_text)

        if category_key == "lawful_presence":
            labels = [option.label for option in category.options] + ["I'm not sure"]
            keys = [option.key for option in category.options] + ["not_sure"]
            current_choice = documents.get("lawful_presence_choice")
            choice_key = f"doc_{category_key}_choice"
            if choice_key not in st.session_state:
                selected_key = current_choice if current_choice in keys else "not_sure"
                st.session_state[choice_key] = labels[keys.index(selected_key)]
            chosen = st.radio(
                "Pick the category that fits",
                labels,
                key=choice_key,
            )
            documents["lawful_presence_choice"] = keys[labels.index(chosen)]
        else:
            labels_map = {option.key: option.label for option in category.options}
            prior_selected = documents["selected"].get(category_key, [])
            prior_selected = [key for key in prior_selected if key in labels_map]
            select_key = f"doc_{category_key}_select"
            if select_key not in st.session_state:
                st.session_state[select_key] = prior_selected
            choices = st.multiselect(
                f"What do you have for {category.title.lower()}?",
                options=list(labels_map.keys()),
                format_func=lambda key: labels_map[key],
                key=select_key,
            )
            documents["selected"][category_key] = choices

            if category.allow_other:
                current_other = documents["other_text"].get(category_key, "")
                other_key = f"doc_{category_key}_other"
                if other_key not in st.session_state:
                    st.session_state[other_key] = current_other
                other_text = st.text_input(
                    f"Other {category.title.lower()} document (describe)",
                    key=other_key,
                    placeholder="e.g. court order, certified school transcript",
                )
                documents["other_text"][category_key] = other_text

            has_document_selection = bool(choices) or bool(documents["other_text"].get(category_key, "").strip())
            current_unsure = bool(documents["unsure"].get(category_key, False))
            current_none = bool(documents["none"].get(category_key, False))
            if current_unsure and current_none:
                current_unsure = False
                documents["unsure"][category_key] = False
            unsure_key = f"doc_{category_key}_unsure"
            if has_document_selection:
                st.session_state[unsure_key] = False
                documents["unsure"][category_key] = False
            elif unsure_key not in st.session_state:
                st.session_state[unsure_key] = current_unsure
            documents["unsure"][category_key] = st.checkbox(
                f"I'm not sure about {category.title.lower()}",
                key=unsure_key,
                disabled=has_document_selection or current_none,
                help="Clear selected documents and the 'I don't have any' option first if you want to mark this as unsure.",
            )
            none_key = f"doc_{category_key}_none"
            if has_document_selection:
                st.session_state[none_key] = False
                documents["none"][category_key] = False
            elif none_key not in st.session_state:
                st.session_state[none_key] = current_none
            documents["none"][category_key] = st.checkbox(
                f"I don't have any {category.title.lower()} documents",
                key=none_key,
                disabled=has_document_selection or documents["unsure"].get(category_key, False),
                help="Clear selected documents and the unsure option first if you want to mark that you do not have any.",
            )

        st.caption(category.note)


def render_review_step(session: AssistantSession, form_state: dict[str, Any]) -> None:
    facts_preview = preview_facts(session, form_state)
    documents_preview = form_state.get("documents", {})

    with st.container(border=True):
        st.markdown("**Your answers**")
        st.json(facts_preview, expanded=False)

        selected = documents_preview.get("selected", {})
        has_selected_documents = any(selected.get(key) for key in selected) or documents_preview.get("lawful_presence_choice")
        if has_selected_documents:
            st.markdown("**Documents you picked**")
            for category_key, choices in selected.items():
                if not choices:
                    continue
                human = ", ".join(option_label(category_key, key) for key in choices)
                st.markdown(f"- **{DOCUMENT_CATEGORIES[category_key].title}**: {human}")
            if documents_preview.get("lawful_presence_choice"):
                st.markdown(
                    f"- **Citizenship or lawful presence**: {option_label('lawful_presence', documents_preview['lawful_presence_choice'])}"
                )
        else:
            st.caption("You haven't recorded specific documents yet. The rules engine will list what's expected.")


def preview_facts(session: AssistantSession, form_state: dict[str, Any]) -> dict[str, Any]:
    facts = facts_from_intake(form_state["scenario"], dict(form_state["values"]))
    facts = merge_facts(replace_facts(session.facts), facts, allow_overwrite=True)
    documents = build_documents_from_state(form_state)
    facts = apply_document_selections(facts, documents)
    return facts.to_public_dict()


def replace_facts(facts: FactState) -> FactState:
    return replace(facts, source_notes=list(facts.source_notes))


def build_documents_from_state(form_state: dict[str, Any]) -> DocumentSelections:
    docs = form_state.get("documents", {})
    return DocumentSelections(
        selected=dict(docs.get("selected", {})),
        other_text=dict(docs.get("other_text", {})),
        unsure=dict(docs.get("unsure", {})),
        none=dict(docs.get("none", {})),
        lawful_presence_choice=docs.get("lawful_presence_choice"),
    )


def render_step_nav(
    session: AssistantSession,
    scenario_key: str,
    current_index: int,
    total: int,
    settings: dict[str, bool],
) -> None:
    st.divider()
    if current_index == 0:
        next_title = steps_for(scenario_key)[current_index + 1].title if current_index + 1 < total else "Review and check"
        with st.container(border=True, key="step_nav_single"):
            copy_col, action_col = st.columns([1, 0.38], vertical_alignment="center")
            with copy_col:
                st.markdown(
                    f'<p class="step-nav-copy">Next: <strong>{escape(next_title)}</strong></p>',
                    unsafe_allow_html=True,
                )
            with action_col:
                if st.button("Continue", key="step_continue", use_container_width=True):
                    session.intake_step = current_index + 1
                    st.session_state.assistant_session = session
                    st.rerun()
        return

    if current_index < total - 1:
        back_col, next_col = st.columns(2)
        with back_col:
            if st.button("Back", key="step_back", use_container_width=True):
                session.intake_step = current_index - 1
                st.session_state.assistant_session = session
                st.rerun()
        with next_col:
            if st.button("Continue", key="step_continue", use_container_width=True):
                session.intake_step = current_index + 1
                st.session_state.assistant_session = session
                st.rerun()
        return

    back_col, run_col = st.columns(2)
    with back_col:
        if st.button("Back", key="step_back", use_container_width=True):
            session.intake_step = current_index - 1
            st.session_state.assistant_session = session
            st.rerun()
    with run_col:
        if st.button("Check my requirements", key="step_run", type="primary", use_container_width=True):
            run_reasoning(session, scenario_key, settings)
            st.rerun()
    st.caption("The s(CASP) rule engine runs once when you click Check my requirements.")


def run_reasoning(session: AssistantSession, scenario_key: str, settings: dict[str, bool]) -> None:
    form_state = st.session_state.get("intake_form_state")
    if not form_state:
        form_state = ensure_form_state(session, scenario_key)

    intake_facts = facts_from_intake(scenario_key, dict(form_state["values"]))
    documents = build_documents_from_state(form_state)
    intake_facts = apply_document_selections(intake_facts, documents)

    session.facts = merge_facts(session.facts, intake_facts, allow_overwrite=True)
    session.documents = documents
    session.last_policy_result = run_policy_safely(session.facts)
    st.session_state["followup_messages"] = []
    st.session_state.pop("report_summary", None)

    if session.last_policy_result.error is None:
        report = compose_report(session.facts, session.last_policy_result, session.documents)
        summary = generate_summary(
            session.facts,
            session.last_policy_result,
            session.documents,
            report,
            GeminiSummaryConfig.from_env(enabled=settings["summary"]),
        )
        st.session_state["report_summary"] = summary
        append_assistant_turn(session, summary)
    else:
        append_assistant_turn(
            session,
            "I couldn't run the s(CASP) rule engine. Make sure `scasp` is installed and on PATH, then try again.",
        )
    st.session_state.assistant_session = session


# ----------------- Step 3: report + follow-up -----------------


def render_report_and_followup(session: AssistantSession, settings: dict[str, bool]) -> None:
    result = session.last_policy_result
    if not result:
        return

    if result.error:
        st.error(result.error)
        if st.button("Update my answers", key="error_update"):
            session.last_policy_result = None
            st.session_state.assistant_session = session
            st.rerun()
        return

    report = compose_report(session.facts, result, session.documents)
    summary = st.session_state.get("report_summary")
    if summary is None:
        summary = generate_summary(
            session.facts,
            result,
            session.documents,
            report,
            GeminiSummaryConfig.from_env(enabled=settings["summary"]),
        )
        st.session_state["report_summary"] = summary

    render_report_header(report)
    render_summary_panel(summary)
    render_report_body(report)
    render_missing_section(report)
    render_next_steps(report)
    render_post_actions(session)
    render_followup_chat(session, settings, report)
    render_scasp_run_details(session)


def render_report_header(report: Report) -> None:
    st.markdown(
        f"""
        <div class="result-header">
            <div class="result-eyebrow">Guidance report</div>
            <div class="result-title">{escape(report.case_title)}</div>
            <div class="result-subtitle">{escape(report.case_outcome)}</div>
            <div class="result-stats">
                <div class="result-stat">
                    <div class="result-stat-label">Application / service method</div>
                    <div class="result-stat-value">{escape(report.service_method or "Not yet determined")}</div>
                </div>
                <div class="result-stat">
                    <div class="result-stat-label">Items still missing</div>
                    <div class="result-stat-value">{len(report.missing_items)}</div>
                </div>
                <div class="result-stat">
                    <div class="result-stat-label">Confidence note</div>
                    <div class="result-stat-value">{escape(report.confidence_note)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_panel(summary: str) -> None:
    st.markdown(
        f"""
        <div class="summary-panel">
            <div class="summary-label">Personalized summary</div>
            <div>{markdown_to_basic_html(summary)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report_body(report: Report) -> None:
    for section in report.sections:
        with st.container(border=True):
            render_report_section(section)


def render_report_section(section: ReportSection) -> None:
    st.markdown(f"### {section.icon} {section.title}".strip())
    if section.summary:
        st.caption(section.summary)
    if not section.items and not section.bullets:
        st.markdown(f'<div class="empty-text">{escape(section.empty_text)}</div>', unsafe_allow_html=True)
        return
    if section.items:
        items_html = "".join(checklist_item_html(item) for item in section.items)
        st.markdown(f'<ul class="checklist">{items_html}</ul>', unsafe_allow_html=True)
    if section.bullets:
        for bullet in section.bullets:
            st.markdown(f"- {bullet}")


def checklist_item_html(item: ChecklistItem) -> str:
    marker = {
        "confirmed": "✅",
        "todo": "🟡",
        "info": "ℹ️",
    }.get(item.status, "•")
    badge = ""
    if item.status == "confirmed":
        badge = '<span class="badge confirmed">Confirmed</span>'
    elif item.status == "todo":
        badge = '<span class="badge todo">To do</span>'
    elif item.status == "info":
        badge = '<span class="badge info">Info</span>'
    detail = f'<div class="detail">{escape(item.detail)}</div>' if item.detail else ""
    return (
        f'<li><span class="marker">{marker}</span><div>{badge}{escape(item.label)}{detail}</div></li>'
    )


def render_missing_section(report: Report) -> None:
    with st.container(border=True):
        st.markdown("### ❓ Missing or unclear items")
        st.caption("Inputs the rule engine still needs before the guidance is complete.")
        if not report.missing_items:
            st.markdown('<div class="empty-text">No items are missing or unclear.</div>', unsafe_allow_html=True)
            return
        checklist = "".join(
            checklist_item_html(ChecklistItem(label=item, status="todo"))
            for item in report.missing_items
        )
        st.markdown(f'<ul class="checklist">{checklist}</ul>', unsafe_allow_html=True)


def render_next_steps(report: Report) -> None:
    with st.container(border=True):
        st.markdown("### ✅ Recommended next steps")
        st.caption("Actions the rule engine recommends based on your current facts.")
        if not report.next_steps:
            st.markdown('<div class="empty-text">No next steps were emitted by the rule engine.</div>', unsafe_allow_html=True)
            return
        items = "".join(f"<li>{escape(step)}</li>" for step in report.next_steps)
        st.markdown(f'<ul class="why-list">{items}</ul>', unsafe_allow_html=True)


def render_scasp_run_details(session: AssistantSession) -> None:
    result = session.last_policy_result
    with st.expander("s(CASP) run: raw facts, queries, and outputs", expanded=False):
        facts_tab, queries_tab, atoms_tab, raw_tab = st.tabs(
            ["Facts sent", "Queries", "Result atoms", "Raw JSON"]
        )
        with facts_tab:
            st.code(scasp_predicates_for_display(session), language="prolog")
        with queries_tab:
            st.json(scasp_queries_for_display())
        with atoms_tab:
            st.json(scasp_result_for_display(session))
        with raw_tab:
            st.json(result.raw if result and result.raw else {})


def render_post_actions(session: AssistantSession) -> None:
    cols = st.columns(2)
    with cols[0]:
        if st.button("Update my answers", key="post_update", use_container_width=True):
            session.last_policy_result = None
            session.intake_step = 0
            st.session_state.assistant_session = session
            st.session_state.pop("report_summary", None)
            st.rerun()
    with cols[1]:
        if st.button("Start over", key="post_reset", use_container_width=True):
            reset_all_state()
            st.rerun()


def render_followup_chat(session: AssistantSession, settings: dict[str, bool], report: Report) -> None:
    st.divider()
    st.markdown("### Ask a follow-up question")
    st.caption('Follow-ups stay grounded in your stored facts and the s(CASP) result. Try: "What counts as proof of identity?"')

    followup_messages: list[ChatMessage] = st.session_state.setdefault("followup_messages", [])
    if followup_messages:
        for message in followup_messages[-6:]:
            with st.container(border=True):
                st.caption("You" if message.role == "user" else "Assistant")
                st.markdown(message.content)
    else:
        st.caption("No follow-up questions yet.")

    follow_up = st.chat_input(
        "Ask about a document, test, waiver, next step, or update one of your answers",
        key="followup_chat_input",
    )

    if not follow_up or not follow_up.strip():
        return

    follow_up = follow_up.strip()
    render_followup_turn(ChatMessage(role="user", content=follow_up))
    assistant_live = st.empty()
    with assistant_live.container():
        with st.container(border=True):
            st.caption("Assistant")
            st.markdown('<div class="followup-pending">Working from your current report...</div>', unsafe_allow_html=True)

    session.messages.append(ChatMessage(role="user", content=follow_up))
    followup_messages.append(ChatMessage(role="user", content=follow_up))
    next_question = session.last_policy_result.next_question if session.last_policy_result else None
    parsed = parse_with_gemini_or_fallback(
        follow_up,
        GeminiParserConfig.from_env(enabled=settings["parser"]),
        current_facts=session.facts,
        next_question=next_question,
    )
    before = state_snapshot(session)
    if should_apply_followup_facts(follow_up, parsed, next_question=next_question):
        session.documents = reconcile_followup_documents(follow_up, parsed.facts, session.documents)
        session.facts = merge_facts(
            session.facts,
            parsed.facts,
            allow_overwrite=parsed.correction or parsed.source != "gemini",
        )
    session.last_parse_result = parsed

    if state_snapshot(session) != before:
        session.facts = apply_document_selections(session.facts, session.documents)
        session.last_policy_result = run_policy_safely(session.facts)
        report = compose_report(session.facts, session.last_policy_result, session.documents)
        st.session_state["report_summary"] = generate_summary(
            session.facts,
            session.last_policy_result,
            session.documents,
            report,
            GeminiSummaryConfig.from_env(enabled=settings["summary"]),
        )

    followup_config = FollowUpConfig.from_env(enabled=settings["followup"])
    answer = answer_follow_up(
        follow_up,
        session.facts,
        session.last_policy_result,
        session.documents,
        report,
        followup_config,
    )
    if state_snapshot(session) != before:
        answer = "I updated your answers and regenerated the report.\n\n" + answer
    with assistant_live.container():
        with st.container(border=True):
            st.caption("Assistant")
            st.write_stream(stream_text(answer))
    append_assistant_turn(session, answer)
    followup_messages.append(ChatMessage(role="assistant", content=answer))
    st.session_state["followup_messages"] = followup_messages
    st.session_state.assistant_session = session
    st.rerun()


def render_followup_turn(message: ChatMessage) -> None:
    with st.container(border=True):
        st.caption("You" if message.role == "user" else "Assistant")
        st.markdown(message.content)


def stream_text(text: str):
    for index, token in enumerate(text.split(" ")):
        if index:
            yield " "
        yield token
        time.sleep(0.012)


def state_snapshot(session: AssistantSession) -> dict[str, Any]:
    return {
        "facts": session.facts.to_public_dict(),
        "documents": {
            "selected": session.documents.selected,
            "other_text": session.documents.other_text,
            "unsure": session.documents.unsure,
            "none": session.documents.none,
            "lawful_presence_choice": session.documents.lawful_presence_choice,
        },
    }


def scasp_predicates_for_display(session: AssistantSession) -> str:
    return ScaspRunner()._facts_to_scasp(session.facts)


def scasp_queries_for_display() -> dict[str, dict[str, object]]:
    return {
        key: {
            "query": query,
            "variable": variable,
            "many": many,
        }
        for key, (query, variable, many) in ScaspRunner.QUERIES.items()
    }


def scasp_result_for_display(session: AssistantSession) -> dict[str, object]:
    result = session.last_policy_result
    if not result:
        return {}
    return {
        "inferred_case": result.case_type,
        "missing_info": result.missing_info,
        "next_question": result.next_question,
        "service_mode": result.service_modes,
        "required_doc": result.required_docs,
        "likely_exam": result.likely_exams,
        "waiver": result.waivers,
        "explanation": result.explanations,
        "final_guidance": result.final_guidance,
        "error": result.error,
    }


def markdown_to_basic_html(text: str) -> str:
    html = escape(text)
    parts = html.split("**")
    if len(parts) > 1:
        rendered: list[str] = []
        for index, part in enumerate(parts):
            if index % 2 == 1:
                rendered.append(f"<strong>{part}</strong>")
            else:
                rendered.append(part)
        html = "".join(rendered)
    return html.replace("\n\n", "<br/><br/>").replace("\n", "<br/>")


# ----------------- Main flow -----------------


def main() -> None:
    inject_styles()
    settings = settings_block()
    session = get_session()
    render_header()

    if session.last_policy_result is not None:
        render_report_and_followup(session, settings)
    elif session.detected_case is not None:
        render_intake(session, settings)
    else:
        render_entry(session, settings)


if __name__ == "__main__":
    main()
