# Texas Driver License Guidance Assistant

Computational Logic Project Writeup

## Project Overview

My project is a Texas Driver License Guidance Assistant. It is an educational expert system that helps users understand common adult, non-commercial Texas driver license scenarios. The supported cases include first-time adult applications, out-of-state license transfers, Texas license renewals, and replacement of a lost, stolen, or damaged Texas license.

The user starts with a plain-English description or a quick-start scenario. The app detects the likely case, asks guided intake questions, converts the answers into logic facts, runs an `s(CASP)` rule program, and returns a structured guidance report. The report includes the likely service method, document categories, likely exams or waivers, missing information, and recommended next steps.

This is not an official Texas DPS system and is not legal advice. It is a class project that demonstrates how a rule-based logic program can make a conversational assistant more grounded, explainable, and consistent.

## Computational Logic Component

The main logic component is `scasp/tx_dl_assistant.pl`. That file is the source of truth for the policy reasoning. The Python code does not make the final decision by itself. Instead, Python collects and normalizes user facts, serializes them into `s(CASP)` predicates, runs the `s(CASP)` executable, and formats the returned atoms into readable output.

The project uses logic rules to model cases such as:

- A new Texas resident with a valid, unexpired out-of-state license is treated as an out-of-state transfer.
- First-time adult applicants are routed to an in-person original application flow.
- Renewal eligibility is handled conservatively because the app should not assume online eligibility unless the required facts are known.
- Replacement cases ask for online replacement identifiers such as card number, date of birth, last-four SSN, and audit number.

The benefit of using `s(CASP)` is that the reasoning is declarative and inspectable. The app can show the raw facts sent to the rule engine, the queries that were run, and the result atoms returned by the logic program.

## How the Project Is Organized


| File or folder                | Purpose                                                                      |
| ----------------------------- | ---------------------------------------------------------------------------- |
| `app.py`                      | Streamlit user interface, guided flow, report rendering, and follow-up chat. |
| `backend/case_detection.py`   | Detects the user scenario from the entry message.                            |
| `backend/intake.py`           | Defines scenario-specific intake questions and maps answers into facts.      |
| `backend/document_catalog.py` | Stores document categories and examples used by the guided selectors.        |
| `backend/scasp_runner.py`     | Converts Python facts to `s(CASP)` predicates and runs the logic engine.     |
| `backend/report_composer.py`  | Converts logic atoms into a structured user report.                          |
| `backend/followup.py`         | Answers follow-up questions using the stored facts and latest logic result.  |
| `scasp/tx_dl_assistant.pl`    | Main rule base for the project.                                              |


## How to Run It

Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Make sure `s(CASP)` is installed and available:

```bash
scasp --version
```

Start the app:

```bash
streamlit run app.py
```

Open the local URL shown by Streamlit, usually:

```text
http://localhost:8501
```

## Sample Run

A representative run uses this scenario:

> I moved to Texas and have a valid unexpired out-of-state driver license.

The app detects this as an out-of-state transfer case. The guided intake confirms the user's age, new Texas resident status, out-of-state license status, vehicle and insurance facts, and available document categories. After the review screen, the app runs the `s(CASP)` rule engine once and produces a structured report.

The report routes the case to an in-person Texas DPS transfer flow. It also explains that knowledge and skills exam waivers likely apply because the user has a valid, unexpired out-of-state license. The follow-up chat stays grounded in the same stored facts and latest rule result.

## Lessons Learned

The biggest lesson from this project was that a conversational app needs more than fluent language. A user can describe a situation naturally, but the system still has to remember the facts, identify what is missing, apply rules consistently, and explain why it reached a conclusion. The project works best when the natural-language layer is treated as an input and presentation layer, while the logic program remains responsible for the decision.

I also learned why domain-specific design matters. A driver license assistant cannot be completely open-ended if it is supposed to give useful guidance. It needs a defined set of scenarios, a document catalog, a clear intake flow, and rules for when information is missing. That narrower design makes the system less general, but it also makes the answers more reliable.

Another lesson was the importance of follow-up questions. The final report is useful, but users often need to ask things like what counts as proof of identity or why an exam was waived. Keeping follow-ups grounded in the stored facts and latest `s(CASP)` result prevents the conversation from drifting away from the actual case.

Finally, I learned that explainability is one of the main advantages of symbolic reasoning. The app can expose the predicates, queries, and result atoms behind a recommendation. That makes the project easier to debug and also makes the final answer easier to trust, because the user can see that the guidance came from explicit facts and rules rather than an unsupported generated response.
