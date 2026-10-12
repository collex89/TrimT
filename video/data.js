window.DATA = {
 "total": 44.0,
 "premium": "gemini-3.8-flash",
 "thinking": 282,
 "prefix_tokens": 2197,
 "prefix_calls": 6,
 "terminal": [
  [
   "p",
   "$ python -m demo_agent.run wasteful",
   "type"
  ],
  [
   "dim",
   "  2 tickets \u00b7 12 LLM calls traced to neatlogs",
   "line"
  ],
  [
   "",
   " ",
   "line"
  ],
  [
   "p",
   "$ python -m trimt traces/wasteful.jsonl --after traces/fixed.jsonl --judge",
   "type"
  ],
  [
   "",
   "  - Overpowered model  classify_intent",
   "line"
  ],
  [
   "r",
   "      $0.01692 -> $0.00303",
   "line"
  ],
  [
   "",
   "  - Repeated prompt    classify_intent",
   "line"
  ],
  [
   "r",
   "      $0.00989 -> $0.00247",
   "line"
  ],
  [
   "",
   "  - Redundant call     extract_keywords",
   "line"
  ],
  [
   "r",
   "      $0.00317 -> $0.00000",
   "line"
  ],
  [
   "ok",
   "  run total: $0.02126 -> $0.00381 (est. 82% saved)",
   "line"
  ],
  [
   "ok",
   "  answer check: q1 same answer",
   "line"
  ]
 ],
 "shot": {
  "file": "report.png",
  "width": 1200
 },
 "receipt_box": {
  "x": 211,
  "y": 454.1875,
  "w": 778,
  "h": 138
 },
 "findings": [
  {
   "title": "Overpowered model",
   "detail": "Simple steps on the premium model<br>$0.01692 \u2192 $0.00303 per ticket",
   "box": {
    "x": 211,
    "y": 592.6875,
    "w": 778,
    "h": 161.25
   }
  },
  {
   "title": "Repeated prompt",
   "detail": "The same big prompt, resent every call<br>$0.00989 \u2192 $0.00247 per ticket",
   "box": {
    "x": 211,
    "y": 753.9375,
    "w": 778,
    "h": 120.75
   }
  },
  {
   "title": "Redundant call",
   "detail": "The same request, made twice<br>$0.00317 \u2192 $0.00000 per ticket",
   "box": {
    "x": 211,
    "y": 874.6875,
    "w": 778,
    "h": 77.5
   }
  }
 ],
 "total_box": {
  "x": 211,
  "y": 958.1875,
  "w": 778,
  "h": 42
 },
 "before": "$0.02126",
 "after": "$0.00556",
 "pct": 74,
 "per1k_before": "$21.26",
 "per1k_after": "$5.56",
 "verdicts": [
  "q1 same answer"
 ],
 "n_measured": 1
};
