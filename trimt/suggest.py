"""Plain-English fixes for findings.

Each detector already writes a template suggestion. With ``--llm-suggestions`` the
wording is rewritten by a cheap model, given only the finding's facts. Numbers always
come from code: the model never sees or writes the costs shown in the report.
"""

from google import genai

from .records import Finding

MODEL = "gemini-3.1-flash-lite"

PROMPT = """\
Rewrite this cost-saving suggestion for an AI agent's developer as one short sentence
(under 30 words). Be specific to the step. Do not mention prices, dollar amounts or
percentages. Reply with the sentence only.

Step: {step}
Problem found: {detector} - {evidence}
Current suggestion: {suggestion}"""


def rewrite_suggestions(findings: list[Finding], client: genai.Client | None = None) -> None:
    client = client or genai.Client()
    for f in findings:
        try:
            r = client.models.generate_content(
                model=MODEL,
                contents=PROMPT.format(
                    step=f.step, detector=f.detector, evidence=f.evidence, suggestion=f.suggestion
                ),
                config={"temperature": 0},
            )
        except genai.errors.APIError:
            continue  # keep the template wording
        text = (r.text or "").strip()
        if text and "$" not in text:
            f.suggestion = text
