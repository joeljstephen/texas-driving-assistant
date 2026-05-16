# Texas Driver License Guidance Assistant

An educational expert system that helps adults understand common non-commercial Texas driver license scenarios.

The assistant starts from a plain-language message or quick-start scenario, identifies the likely case, asks guided intake questions, turns the answers into logic facts, runs an `s(CASP)` rule program, and returns a structured guidance report. The report includes the likely service method, document categories, likely exams or waivers, missing information, and recommended next steps.

## Important Disclaimer

This project is for educational expert-system work only. It is not legal advice and it is not an official Texas DPS or Texas.gov service. Always verify requirements, eligibility, fees, deadlines, forms, documents, and procedures with official Texas DPS or Texas.gov sources before acting.

## Supported Scenarios

- First-time adult Texas driver license application
- Moving to Texas with a valid, unexpired out-of-state driver license
- Texas driver license renewal
- Replacement of a lost, stolen, or damaged Texas driver license
- Address or name change through the replacement/change-info flow

Out of scope: under-18 licensing paths, learner permits, CDL, motorcycle endorsement logic, suspensions, revocations, reinstatement, medical advisory board cases, complex immigration edge cases, appointment booking, payment processing, and real government service integration.

## How It Works

1. The user enters a natural-language message or starts from a quick scenario.
2. Case detection selects the most likely guided intake flow.
3. The intake collects only the facts needed for that scenario, including document category selections.
4. The Python app serializes the facts into `s(CASP)` predicates.
5. `scasp/tx_dl_assistant.pl` classifies the case and emits policy atoms.
6. The report composer turns those atoms into a user-facing report.
7. Follow-up answers stay grounded in the stored facts and latest `s(CASP)` result.

`s(CASP)` is the source of truth for decisions. Optional Gemini calls may help parse free text, rewrite a summary, or lightly rephrase follow-up answers, but they are not allowed to add or override requirements.

## Tech Stack

- Python 3.11+
- Streamlit for the UI
- `s(CASP)` for rule-based reasoning
- Google Gemini, optional, for structured parsing and wording polish

## Project Structure

```text
app.py                         Streamlit app and UI flow
backend/case_detection.py      Entry-message scenario detection
backend/intake.py              Guided intake steps and fact mapping
backend/document_catalog.py    Curated document categories
backend/parser.py              Deterministic regex parser
backend/gemini_parser.py       Optional Gemini structured parser
backend/scasp_runner.py        s(CASP) subprocess integration
backend/report_composer.py     Structured report assembly
backend/gemini_summary.py      Optional grounded summary rewrite
backend/followup.py            Grounded follow-up answers
backend/followup_state.py      Follow-up fact/document reconciliation
backend/response_generator.py  Atom labels for reports and summaries
scasp/tx_dl_assistant.pl       Policy rules source of truth
```

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Install `s(CASP)`

The app expects a local `scasp` executable on `PATH`.

One common installation path is through SWI-Prolog packs:

```prolog
?- pack_install(scasp).
```

Verify from your shell:

```bash
scasp --version
```

If `scasp` is missing, the app shows a setup error instead of falling back to Python policy logic.

## Optional Gemini Configuration

Gemini is optional. Without it, the deterministic parser, deterministic summary, and deterministic follow-up answers still work.

```bash
cp .env.example .env
```

Set the values you want:

```bash
GEMINI_API_KEY=
GEMINI_MODEL=
ENABLE_GEMINI_PARSER=true
ENABLE_GEMINI_SUMMARY=false
ENABLE_GEMINI_FOLLOWUP=false
```

If `GEMINI_API_KEY` is not set, all Gemini-assisted features stay disabled and the deterministic parser, summary, and follow-up paths are used.

## Run

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit, usually [http://localhost:8501](http://localhost:8501).
