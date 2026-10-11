"""SwiftBox support agent, in a wasteful and a fixed version.

Both versions take the same ticket through the same steps:
classify intent -> extract keywords -> draft answer -> check answer -> summarise ticket.

wasteful: every call uses the premium model and resends the handbook plus the whole
          knowledge base; keywords are extracted twice.
fixed:    simple steps use the budget model with short prompts, keywords are extracted
          once, and only the draft and check steps get the handbook (with the top docs).
"""

import re
from dataclasses import dataclass

from trimt.logger import TracedLLM

from .knowledge import DOCS, HANDBOOK, INTENTS

PREMIUM = "gemini-3.8-flash"
BUDGET = "gemini-3.1-flash-lite"

FULL_CONTEXT = HANDBOOK + "\n\nKNOWLEDGE BASE\n\n" + "\n\n".join(
    f"[{name}]\n{text}" for name, text in DOCS.items()
)


@dataclass
class TicketResult:
    intent: str
    answer: str
    check: str
    summary: str


def _prompts(question: str):
    return {
        "classify": f"Classify this customer message into exactly one of these intents: "
        f"{', '.join(INTENTS)}. Reply with the intent label only.\n\nMessage: {question}",
        "keywords": f"Extract up to 6 search keywords from this customer message. "
        f"Reply with a comma-separated list only.\n\nMessage: {question}",
        "summary": "Summarise this support ticket in one line for the ticket queue, "
        "starting with the priority (P1, P2 or P3).",
    }


def search_docs(keywords: str, k: int = 2) -> list[str]:
    """Plain keyword-overlap search over the knowledge base. Returns doc names."""
    words = {w for w in re.findall(r"[a-z]+", keywords.lower()) if len(w) > 2}
    scored = sorted(
        DOCS,
        key=lambda name: -sum(text.lower().count(w) for w in words for text in [DOCS[name]]),
    )
    return scored[:k]


def run_wasteful(llm: TracedLLM, question: str) -> TicketResult:
    p = _prompts(question)
    intent = llm.generate(step="classify_intent", model=PREMIUM, system=FULL_CONTEXT, prompt=p["classify"])
    keywords = llm.generate(step="extract_keywords", model=PREMIUM, system=FULL_CONTEXT, prompt=p["keywords"])

    answer = llm.generate(
        step="draft_answer",
        model=PREMIUM,
        system=FULL_CONTEXT,
        prompt=f"Intent: {intent.strip()}\nSearch keywords: {keywords.strip()}\n\n"
        f"Customer message: {question}\n\nWrite the reply to the customer.",
    )

    # The checker re-derives the keywords instead of reusing the ones above.
    keywords_again = llm.generate(step="extract_keywords", model=PREMIUM, system=FULL_CONTEXT, prompt=p["keywords"])
    check = llm.generate(
        step="check_answer",
        model=PREMIUM,
        system=FULL_CONTEXT,
        prompt=f"Customer message: {question}\nKeywords: {keywords_again.strip()}\n\nDraft reply:\n{answer}\n\n"
        "Does the draft follow the handbook and only use facts from the knowledge base? "
        "Reply PASS or FAIL and one short reason.",
    )
    summary = llm.generate(
        step="summarise_ticket",
        model=PREMIUM,
        system=FULL_CONTEXT,
        prompt=f"{p['summary']}\n\nCustomer message: {question}\nReply sent: {answer}",
    )
    return TicketResult(intent.strip(), answer.strip(), check.strip(), summary.strip())


def run_fixed(llm: TracedLLM, question: str) -> TicketResult:
    p = _prompts(question)
    intent = llm.generate(step="classify_intent", model=BUDGET, prompt=p["classify"])
    keywords = llm.generate(step="extract_keywords", model=BUDGET, prompt=p["keywords"])
    docs = search_docs(f"{intent} {keywords} {question}")
    context = "\n\n".join(f"[{name}]\n{DOCS[name]}" for name in docs)

    answer = llm.generate(
        step="draft_answer",
        model=PREMIUM,
        system=HANDBOOK,
        prompt=f"KNOWLEDGE BASE (most relevant articles)\n\n{context}\n\n"
        f"Intent: {intent.strip()}\nSearch keywords: {keywords.strip()}\n\n"
        f"Customer message: {question}\n\nWrite the reply to the customer.",
    )
    check = llm.generate(
        step="check_answer",
        model=BUDGET,
        system=HANDBOOK,
        prompt=f"KNOWLEDGE BASE (most relevant articles)\n\n{context}\n\n"
        f"Customer message: {question}\nKeywords: {keywords.strip()}\n\nDraft reply:\n{answer}\n\n"
        "Does the draft follow the handbook and only use facts from the knowledge base? "
        "Reply PASS or FAIL and one short reason.",
    )
    summary = llm.generate(
        step="summarise_ticket",
        model=BUDGET,
        prompt=f"{p['summary']}\nPriorities: P1 safety, legal threats or urgent documents/medicine; "
        f"P2 lost, damaged, wrong or repeatedly failed delivery; P3 everything else."
        f"\n\nCustomer message: {question}\nReply sent: {answer}",
    )
    return TicketResult(intent.strip(), answer.strip(), check.strip(), summary.strip())


AGENTS = {"wasteful": run_wasteful, "fixed": run_fixed}
