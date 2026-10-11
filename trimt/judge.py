"""Checks that the fixed agent still gives the customer the same answer."""

from google import genai

MODEL = "gemini-3.1-flash-lite"  # its own free quota, separate from the agent's premium model

PROMPT = """\
Two support replies answer the same customer message. Do they give the customer the same
facts and the same next step? Ignore wording, tone and length.

Customer message: {question}

Reply A:
{a}

Reply B:
{b}

Answer "SAME: <reason>" or "DIFFERENT: <what differs>", in one line."""


def judge_answers(question: str, a: str, b: str, client: genai.Client) -> str:
    r = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(question=question, a=a, b=b),
        config={"temperature": 0},
    )
    return (r.text or "").strip().splitlines()[0] if r.text else "UNKNOWN: empty reply"
