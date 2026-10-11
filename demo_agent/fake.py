"""A stand-in Gemini client for --dry-run: no API calls, no quota used.

Token counts are estimated (about 4 characters per token) and premium models get a
fixed amount of "thinking", so the whole pipeline and report can be exercised offline.
Dry-run traces are for testing only, never for the demo numbers.
"""

from types import SimpleNamespace

REASONING_MODELS = ("gemini-3.8-flash",)

CANNED = {
    "classify_intent": "claim",
    "extract_keywords": "parcel, damaged, refund, claim, delivery",
    "check_answer": "PASS - follows the handbook and uses only knowledge-base facts.",
    "summarise_ticket": "P2 - Customer reports a damaged parcel; told how to open a claim in the app.",
}
DEFAULT_ANSWER = (
    "Sorry your parcel arrived damaged. You can open a claim in the app under Help > My parcel > "
    "Make a claim within 7 days of the expected delivery date. Upload photos of the item and the "
    "packaging before throwing anything away. Claims are reviewed within 3 working days, and if "
    "yours is approved the payout goes back to your original payment method. Next step: open the "
    "claim in the app today."
)


def _step_of(prompt: str) -> str:
    if prompt.startswith("Classify"):
        return "classify_intent"
    if prompt.startswith("Extract"):
        return "extract_keywords"
    if "Reply PASS or FAIL" in prompt:
        return "check_answer"
    if prompt.startswith("Summarise"):
        return "summarise_ticket"
    if "Reply A:" in prompt:
        return "judge"
    return "draft_answer"


class _Models:
    def generate_content(self, *, model, contents, config=None):
        system = getattr(config, "system_instruction", None) or ""
        step = _step_of(contents)
        text = "SAME: both give the same facts and next step." if step == "judge" else CANNED.get(step, DEFAULT_ANSWER)
        reasoning = 300 if model in REASONING_MODELS else None
        usage = SimpleNamespace(
            prompt_token_count=(len(system) + len(contents)) // 4,
            candidates_token_count=max(len(text) // 4, 1),
            thoughts_token_count=reasoning,
            cached_content_token_count=None,
        )
        return SimpleNamespace(text=text, usage_metadata=usage, model_version=model)


class FakeClient:
    def __init__(self):
        self.models = _Models()
