import pytest

from trimt.analyze import analyze_run
from trimt.config import load_config
from trimt.detectors import overpowered, redundant, repeated_prompt
from trimt.pricing import Pricing
from trimt.records import TraceRecord

PRICING = Pricing.load()
CONFIG = load_config()

SYSTEM = "You are a support agent. " + "Policy text. " * 1500  # ~19.5k chars
PREMIUM = "gemini-3.8-flash"
BUDGET = "gemini-3.1-flash-lite"


def rec(i, step, prompt, model=PREMIUM, out=200, reasoning=0, cached=0, run="r1"):
    return TraceRecord(
        run_id=run,
        step=step,
        call_index=i,
        model=model,
        input_tokens=len(prompt) // 4,  # ~4 chars per token
        output_tokens=out + reasoning,
        reasoning_tokens=reasoning,
        cached_input_tokens=cached,
        prompt=prompt,
        output="x",
    )


# --- pricing -----------------------------------------------------------------

def test_cost_uses_pricing_file():
    # 1M input + 1M output on gemini-3.8-flash = 0.75 + 3.75
    assert PRICING.cost(PREMIUM, 1_000_000, 1_000_000) == pytest.approx(4.50)
    # cached input is billed at the cached rate
    assert PRICING.cost(PREMIUM, 1_000_000, 0, cached_input_tokens=1_000_000) == pytest.approx(0.075)


def test_unknown_model_is_an_error():
    with pytest.raises(KeyError):
        PRICING.get("made-up-model")


# --- overpowered model ---------------------------------------------------------

def test_flags_short_answer_on_premium_model():
    calls = [rec(0, "classify_intent", "Classify: where is my order?", out=3, reasoning=150)]
    [f] = overpowered.detect("r1", calls, PRICING, CONFIG["overpowered_model"])
    assert f.detector == "overpowered_model"
    assert f.step == "classify_intent"
    # after = same input + visible output at the budget model, no thinking tokens
    expected = PRICING.cost(BUDGET, calls[0].input_tokens, 3)
    assert f.cost_after == pytest.approx(expected)
    assert f.cost_now > f.cost_after


def test_flags_keyword_step_even_with_long_output():
    calls = [rec(0, "extract_fields", "Return JSON of the fields.", out=400)]
    assert overpowered.detect("r1", calls, PRICING, CONFIG["overpowered_model"])


def test_simple_steps_in_a_run_are_one_finding():
    calls = [
        rec(0, "classify_intent", "Classify this.", out=2, reasoning=100),
        rec(1, "summarise_ticket", "One-line summary.", out=20, reasoning=100),
        rec(2, "draft_answer", "Write a careful reply.", out=300),
    ]
    [f] = overpowered.detect("r1", calls, PRICING, CONFIG["overpowered_model"])
    assert f.calls == [0, 1]
    assert f.step == "classify_intent, summarise_ticket"
    assert "2 simple steps" in f.evidence


def test_ignores_long_answer_and_cheap_models():
    long_answer = rec(0, "draft_answer", "Write a detailed reply to the customer.", out=400)
    cheap = rec(1, "classify_intent", "Classify this.", model=BUDGET, out=3)
    assert overpowered.detect("r1", [long_answer, cheap], PRICING, CONFIG["overpowered_model"]) == []


def test_keyword_in_long_system_prompt_does_not_count():
    prompt = "Always format replies politely. " + "Policy. " * 500 + "Write a full reply."
    call = rec(0, "draft_answer", prompt, out=300)
    assert overpowered.detect("r1", [call], PRICING, CONFIG["overpowered_model"]) == []


# --- repeated prompt -----------------------------------------------------------

def test_flags_system_prompt_repeated_in_three_calls():
    calls = [rec(i, s, SYSTEM + f"\n\nTask {i}: {s}") for i, s in enumerate(["a", "b", "c"])]
    findings = repeated_prompt.detect("r1", calls, PRICING, CONFIG["repeated_prompt"])
    [f] = [f for f in findings if f.detector == "repeated_prompt"]
    assert f.calls == [0, 1, 2]
    assert "3 calls" in f.evidence
    # first call still pays full price; the other two move to the cached rate
    assert set(f.changes) == {1, 2}
    assert f.cost_after < f.cost_now


def test_two_repeats_are_not_enough():
    calls = [rec(i, s, SYSTEM + s) for i, s in enumerate(["a", "b"])]
    findings = repeated_prompt.detect("r1", calls, PRICING, CONFIG["repeated_prompt"])
    assert [f for f in findings if f.detector == "repeated_prompt"] == []


def test_short_shared_prefix_is_ignored():
    calls = [rec(i, s, "Be brief. " + s * 50) for i, s in enumerate("abc")]
    findings = repeated_prompt.detect("r1", calls, PRICING, CONFIG["repeated_prompt"])
    assert [f for f in findings if f.detector == "repeated_prompt"] == []


def test_already_cached_prefix_saves_less():
    fresh = [rec(i, "s", SYSTEM + str(i)) for i in range(3)]
    cached = [rec(i, "s", SYSTEM + str(i), cached=4000) for i in range(3)]
    cfg = CONFIG["repeated_prompt"]
    [f_fresh] = repeated_prompt.detect("r1", fresh, PRICING, cfg)
    [f_cached] = repeated_prompt.detect("r1", cached, PRICING, cfg)
    assert f_cached.saving < f_fresh.saving


def test_flags_huge_context_for_tiny_answer():
    call = rec(0, "draft_answer", "Docs: " + "lorem ipsum " * 2000 + "\nQ: hours?", out=20)
    findings = repeated_prompt.detect("r1", [call], PRICING, CONFIG["repeated_prompt"])
    [f] = [f for f in findings if f.detector == "large_context"]
    assert f.cost_after == pytest.approx(f.cost_now * 0.3, rel=0.01)


# --- redundant calls -----------------------------------------------------------

def test_flags_identical_calls_ignoring_case_and_whitespace():
    calls = [
        rec(0, "extract_keywords", "Keywords for: Where is my ORDER?"),
        rec(1, "draft_answer", "something else entirely"),
        rec(2, "verify_answer", "keywords  for:\nwhere is my order?"),
    ]
    [f] = redundant.detect("r1", calls, PRICING, CONFIG["redundant_calls"])
    assert f.calls == [2]
    assert f.cost_after == 0
    assert f.cost_now == pytest.approx(PRICING.call_cost(calls[2]))
    assert "Identical" in f.evidence


def test_flags_near_identical_calls():
    base = "Summarise this ticket for the agent queue: " + "details " * 100
    calls = [rec(0, "s", base + "ref 1001"), rec(1, "s", base + "ref 1002")]
    [f] = redundant.detect("r1", calls, PRICING, CONFIG["redundant_calls"])
    assert "Near-identical" in f.evidence


def test_shared_system_prompt_alone_does_not_make_calls_duplicates():
    # Same 19k-char system prompt, different short requests: ~99% similar as whole prompts.
    calls = [
        rec(i, s, SYSTEM + "\n\n" + q)
        for i, (s, q) in enumerate([("classify", "Classify: refund?"), ("keywords", "Keywords: refund?")])
    ]
    for c in calls:
        c.system_chars = len(SYSTEM) + 2
    assert redundant.detect("r1", calls, PRICING, CONFIG["redundant_calls"]) == []


def test_different_models_are_not_duplicates():
    calls = [rec(0, "s", "same prompt"), rec(1, "s", "same prompt", model=BUDGET)]
    assert redundant.detect("r1", calls, PRICING, CONFIG["redundant_calls"]) == []


# --- run totals ----------------------------------------------------------------

def test_run_total_applies_all_fixes_without_double_counting():
    calls = [
        rec(0, "classify_intent", SYSTEM + "\n\nClassify: refund?", out=2, reasoning=100),
        rec(1, "extract_keywords", SYSTEM + "\n\nKeywords: refund?", out=10),
        rec(2, "draft_answer", SYSTEM + "\n\nWrite the reply.", out=300),
        rec(3, "extract_keywords", SYSTEM + "\n\nKeywords: refund?", out=10),
    ]
    run = analyze_run("r1", calls, PRICING, CONFIG)
    detectors = {f.detector for f in run.findings}
    assert {"overpowered_model", "repeated_prompt", "redundant_calls"} <= detectors

    assert run.call_costs_after[3] == 0  # the duplicate call is gone
    assert 0 < run.cost_after < run.cost_now
    # combined saving is never more than the sum of the separate findings
    assert run.saving <= sum(f.saving for f in run.findings) + 1e-12


def test_clean_run_has_no_findings():
    calls = [rec(0, "draft_answer", "Write a careful reply about refunds.", model=BUDGET, out=300)]
    run = analyze_run("r1", calls, PRICING, CONFIG)
    assert run.findings == []
    assert run.cost_after == pytest.approx(run.cost_now)
