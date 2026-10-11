"""Receipt-style HTML report and a CLI summary."""

from datetime import datetime
from html import escape

from .analyze import RunAnalysis
from .pricing import Pricing
from .records import TraceRecord

DETECTOR_LABELS = {
    "overpowered_model": "Overpowered model",
    "repeated_prompt": "Repeated prompt",
    "large_context": "Bloated context",
    "redundant_calls": "Redundant call",
}
PER_N_TICKETS = 1000


def money(x: float) -> str:
    return f"${x:,.2f}" if x >= 1 else f"${x:,.5f}"


def pct(before: float, after: float) -> str:
    return f"{100 * (before - after) / before:.0f}%" if before else "0%"


# --- CLI --------------------------------------------------------------------------

def text_summary(runs: list[RunAnalysis], measured_after: dict[str, float] | None = None) -> str:
    lines = []
    for run in runs:
        lines.append(f"\n{run.run_id}  ({len(run.calls)} calls)")
        for f in run.findings:
            label = DETECTOR_LABELS.get(f.detector, f.detector)
            lines.append(f"  - {label:<18} {f.step}")
            lines.append(f"      {f.evidence}")
            lines.append(f"      {money(f.cost_now)} -> {money(f.cost_after)}   {f.suggestion}")
        if not run.findings:
            lines.append("  no waste found")
        lines.append(
            f"  run total: {money(run.cost_now)} -> {money(run.cost_after)} "
            f"(est. {run.percent_saved:.0f}% saved)"
        )
    before = sum(r.cost_now for r in runs)
    after = sum(r.cost_after for r in runs)
    lines.append(f"\nAll runs: {money(before)} -> {money(after)} estimated ({pct(before, after)} saved)")
    if measured_after:
        cases = {r.case_id for r in runs}
        m_before = sum(r.cost_now for r in runs if r.case_id in measured_after)
        m_after = sum(v for k, v in measured_after.items() if k in cases)
        lines.append(f"Measured after fixes: {money(m_before)} -> {money(m_after)} ({pct(m_before, m_after)} saved)")
    return "\n".join(lines)


# --- HTML -------------------------------------------------------------------------

CSS = """
:root{--paper:#F4F5F2;--card:#FFFFFF;--ink:#15171A;--muted:#5D6168;--rule:#D9DBD5;--red:#D9381E;--green:#1F7A4D}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 Geist,system-ui,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:40px 16px 80px}
.mono,.num{font-family:"Geist Mono",ui-monospace,monospace}
.num{font-variant-numeric:tabular-nums;white-space:nowrap}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;
  border-bottom:2px solid var(--ink);padding-bottom:16px}
.brand{font:800 44px/1 Geist,sans-serif;letter-spacing:-.04em}
.brand span{color:var(--red)}
.tag{color:var(--muted);margin-top:6px}
.meta{font:12px/1.6 "Geist Mono",monospace;color:var(--muted);text-align:right}
.hero{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:28px 0}
.stat{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:16px}
.stat .k{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.stat .v{font:600 26px/1.2 "Geist Mono",monospace;margin-top:6px}
.stat .s{font-size:12px;color:var(--muted)}
.strike{text-decoration:line-through;text-decoration-color:var(--red);text-decoration-thickness:2px;color:var(--muted)}
.red{color:var(--red)} .green{color:var(--green)}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:40px 0 12px}
.receipt{background:var(--card);border:1px solid var(--rule);border-radius:4px;padding:24px 24px 20px;margin-bottom:24px;
  box-shadow:0 1px 0 var(--rule);position:relative}
.receipt::after{content:"";position:absolute;left:0;right:0;bottom:-8px;height:8px;
  background:radial-gradient(circle at 6px 0,transparent 6px,var(--card) 6.5px) 0 0/12px 8px repeat-x}
.rhead{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font:13px "Geist Mono",monospace;
  border-bottom:1px dashed var(--rule);padding-bottom:10px;margin-bottom:10px}
.q{color:var(--muted);font-size:14px;margin:0 0 12px}
table{width:100%;border-collapse:collapse;table-layout:fixed}
td{padding:6px 0;vertical-align:top;overflow-wrap:anywhere}
td.r{text-align:right;padding-left:12px;width:9.5em}
.calls td{font:12.5px "Geist Mono",monospace;color:var(--muted);padding:3px 0}
.item{border-top:1px dashed var(--rule)}
.item .lbl{font-weight:600}
.item .ev{color:var(--muted);font-size:13.5px}
.item .fix{font-size:13.5px;margin-top:2px}
.item .fix::before{content:"→ ";color:var(--red)}
.total td{border-top:2px solid var(--ink);padding-top:10px;font-weight:700}
.total .num{font-size:17px}
.grand{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:4px 12px;
  border-top:2px solid var(--ink);padding-top:10px;margin-top:6px;font-weight:700}
.grand .num{font-size:20px}
.pill{display:inline-block;font:600 11px/1 "Geist Mono",monospace;padding:4px 7px;border-radius:99px;border:1px solid currentColor}
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}
.cmp div{font-size:13.5px;background:var(--paper);border-radius:6px;padding:10px 12px;white-space:pre-wrap}
.cmp b{display:block;font:600 11px "Geist Mono",monospace;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:4px}
.note{font-size:12.5px;color:var(--muted);margin-top:32px;border-top:1px solid var(--rule);padding-top:12px}
@media (max-width:600px){.brand{font-size:34px}.meta{text-align:left}.cmp{grid-template-columns:1fr}.receipt{padding:18px 14px}}
"""


def _calls_table(run: RunAnalysis, pricing: Pricing) -> str:
    rows = []
    for rec in run.calls:
        now = pricing.call_cost(rec)
        after = run.call_costs_after[rec.call_index]
        cost = (
            f'<span class="strike">{money(now)}</span> {money(after)}' if after < now - 1e-12 else money(now)
        )
        rows.append(
            f"<tr><td>{rec.call_index:>2}. {escape(rec.step)} · {escape(rec.model)} · "
            f"{rec.input_tokens:,} in / {rec.output_tokens:,} out"
            f"{f' ({rec.reasoning_tokens:,} thinking)' if rec.reasoning_tokens else ''}</td>"
            f'<td class="r num">{cost}</td></tr>'
        )
    return f'<table class="calls">{"".join(rows)}</table>'


def _receipt(run: RunAnalysis, pricing: Pricing, question: str = "") -> str:
    items = []
    for f in run.findings:
        items.append(
            f'<tr class="item"><td><div class="lbl">{DETECTOR_LABELS.get(f.detector, f.detector)}'
            f' <span class="mono" style="font-weight:400">· {escape(f.step)}</span></div>'
            f'<div class="ev">{escape(f.evidence)}</div><div class="fix">{escape(f.suggestion)}</div></td>'
            f'<td class="r num"><span class="strike">{money(f.cost_now)}</span><br>'
            f'<span class="red">{money(f.cost_after)}</span></td></tr>'
        )
    if not items:
        items.append('<tr class="item"><td colspan="2" class="ev">No waste found in this run.</td></tr>')
    return f"""
<section class="receipt">
  <div class="rhead"><span>RUN {escape(run.run_id)}</span><span>{len(run.calls)} LLM calls</span></div>
  {f'<p class="q">“{escape(question)}”</p>' if question else ''}
  {_calls_table(run, pricing)}
  <table>{''.join(items)}</table>
  <div class="grand"><span>Total per run <span class="pill red">−{run.percent_saved:.0f}%</span></span>
    <span class="num"><span class="strike">{money(run.cost_now)}</span> {money(run.cost_after)}</span></div>
</section>"""


def _comparison(
    runs: list[RunAnalysis],
    after_runs: dict[str, list[TraceRecord]],
    pricing: Pricing,
    answers_before: dict,
    answers_after: dict,
    verdicts: dict[str, str],
) -> str:
    by_case = {r.case_id: r for r in runs}
    after_by_case = {calls[0].case_id: calls for calls in after_runs.values() if calls}
    blocks = []
    for case_id, calls in after_by_case.items():
        before = by_case.get(case_id)
        if not before:
            continue
        after_cost = sum(pricing.call_cost(c) for c in calls)
        a, b = answers_before.get(case_id, {}), answers_after.get(case_id, {})
        verdict = verdicts.get(case_id, "")
        badge = (
            f'<span class="pill {"green" if verdict.startswith("SAME") else "red"}">{escape(verdict.split(":")[0])}</span>'
            if verdict else ""
        )
        answer_html = ""
        if a or b:
            answer_html = f"""<div class="cmp">
  <div><b>Before · intent {escape(a.get('intent', '?'))}</b>{escape(a.get('answer', ''))}</div>
  <div><b>After · intent {escape(b.get('intent', '?'))}</b>{escape(b.get('answer', ''))}</div></div>
  {f'<p class="q" style="margin-top:8px">Answer check: {escape(verdict)}</p>' if verdict else ''}"""
        blocks.append(f"""
<section class="receipt">
  <div class="rhead"><span>CASE {escape(case_id)} · measured</span><span>{badge}</span></div>
  <table>
    <tr><td>Before ({len(before.calls)} calls)</td><td class="r num"><span class="strike">{money(before.cost_now)}</span></td></tr>
    <tr><td>After fixes ({len(calls)} calls)</td><td class="r num">{money(after_cost)}</td></tr>
    <tr class="total"><td>Saved <span class="pill red">−{pct(before.cost_now, after_cost)}</span></td>
      <td class="r num">{money(before.cost_now - after_cost)}</td></tr>
  </table>{answer_html}
</section>""")
    return "".join(blocks)


def html_report(
    runs: list[RunAnalysis],
    pricing: Pricing,
    sources: list[str],
    questions: dict[str, str] | None = None,
    after_runs: dict[str, list[TraceRecord]] | None = None,
    answers_before: dict | None = None,
    answers_after: dict | None = None,
    verdicts: dict[str, str] | None = None,
) -> str:
    questions = questions or {}
    before = sum(r.cost_now for r in runs)
    est_after = sum(r.cost_after for r in runs)
    n_findings = sum(len(r.findings) for r in runs)
    per_run_before = before / len(runs) if runs else 0
    per_run_after = est_after / len(runs) if runs else 0

    measured_stat = ""
    comparison = ""
    if after_runs:
        cases = {c[0].case_id for c in after_runs.values() if c}
        m_before = sum(r.cost_now for r in runs if r.case_id in cases)
        m_after = sum(pricing.call_cost(c) for calls in after_runs.values() for c in calls)
        measured_stat = f"""<div class="stat"><div class="k">Measured after fixes</div>
  <div class="v green">−{pct(m_before, m_after)}</div><div class="s num">{money(m_before)} → {money(m_after)}</div></div>"""
        comparison = "<h2>Before vs after · same questions, rerun with the fixes</h2>" + _comparison(
            runs, after_runs, pricing, answers_before or {}, answers_after or {}, verdicts or {}
        )

    receipts = "".join(_receipt(r, pricing, questions.get(r.case_id, "")) for r in runs)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trim-T report</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800&family=Geist+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><div class="wrap">
<header>
  <div><div class="brand">Trim<span>-</span>T</div><div class="tag">Trim the tokens, keep the answers.</div></div>
  <div class="meta">{len(runs)} runs · {sum(len(r.calls) for r in runs)} LLM calls<br>{escape(', '.join(sources))}<br>{generated}</div>
</header>
<div class="hero">
  <div class="stat"><div class="k">Cost per run</div><div class="v"><span class="strike">{money(per_run_before)}</span></div>
    <div class="s num red">{money(per_run_after)} after fixes</div></div>
  <div class="stat"><div class="k">Per {PER_N_TICKETS:,} runs</div><div class="v">{money(per_run_after * PER_N_TICKETS)}</div>
    <div class="s num">was {money(per_run_before * PER_N_TICKETS)}</div></div>
  <div class="stat"><div class="k">Estimated saving</div><div class="v red">−{pct(before, est_after)}</div>
    <div class="s">{n_findings} findings</div></div>
  {measured_stat}
</div>
<h2>Receipts · one per run</h2>
{receipts}
{comparison}
<p class="note">Costs use the paid-tier list prices in pricing.yaml ({escape(pricing.source)}). Each line's saving is
computed on its own; run totals apply every fix together, so they never count a saving twice. Suggestions may be
worded by a model, but every number on this page is computed from the traces and the price file.</p>
</div></body></html>"""
