window.DATA = {
 "total": 136.65,
 "schedule": {
  "hook": [
   0.0,
   9.02
  ],
  "problem": [
   9.02,
   36.16
  ],
  "logo": [
   36.16,
   42.46
  ],
  "trace": [
   42.46,
   51.98
  ],
  "incidents": [
   51.98,
   76.54
  ],
  "term": [
   76.54,
   83.54
  ],
  "report": [
   83.54,
   97.04
  ],
  "proof": [
   97.04,
   107.47
  ],
  "entire": [
   107.47,
   118.05
  ],
  "cfo": [
   118.05,
   131.65
  ],
  "end": [
   131.65,
   136.65
  ]
 },
 "lines": {
  "hook": [
   {
    "t": 0.45,
    "d": 2.67,
    "text": "AI agents quietly overpay for every step.",
    "file": "65e9dd9637d8.wav"
   },
   {
    "t": 3.34,
    "d": 5.18,
    "text": "Every LLM call is billed by the token, and many agents use the priciest model for everything.",
    "file": "7bfec38632bc.wav"
   }
  ],
  "problem": [
   {
    "t": 9.47,
    "d": 5.17,
    "text": "Here's a real support bot I built. One customer ticket runs through six LLM calls.",
    "file": "3be9cf62045c.wav"
   },
   {
    "t": 14.86,
    "d": 7.01,
    "text": "All six use the premium model. Classifying the ticket returned one word, but burned 282 thinking tokens.",
    "file": "4e6f77ab6b7e.wav"
   },
   {
    "t": 22.09,
    "d": 6.24,
    "text": "The same 2,197-token prompt is resent on every call, and one request is made twice.",
    "file": "a0b087066d3c.wav"
   },
   {
    "t": 28.55,
    "d": 7.11,
    "text": "The answers look fine, so nobody notices. At a thousand tickets that's about $21, and most of it is waste.",
    "file": "7133f7b18139.wav"
   }
  ],
  "logo": [
   {
    "t": 36.61,
    "d": 5.35,
    "text": "So I built Trim-T. It finds the waste in your agent's traces and prices the fix.",
    "file": "ee55d199a9d2.wav"
   }
  ],
  "trace": [
   {
    "t": 42.91,
    "d": 5.76,
    "text": "Every call the agent makes is traced in neatlogs: model, tokens, prompt and answer.",
    "file": "bfd72448fd74.wav"
   },
   {
    "t": 48.89,
    "d": 2.59,
    "text": "Those traces are where the incidents showed up.",
    "file": "d36d3ad6c45b.wav"
   }
  ],
  "incidents": [
   {
    "t": 52.43,
    "d": 6.49,
    "text": "Trim-T reads them and runs three detectors: an overpowered model, a repeated prompt and a redundant call.",
    "file": "58487ad35e61.wav"
   },
   {
    "t": 59.14,
    "d": 4.26,
    "text": "Each fix is priced from the provider's real price list, never guessed by a model.",
    "file": "eaf1a4444f3d.wav"
   },
   {
    "t": 63.62,
    "d": 6.84,
    "text": "The runs also hit real failures: rate limits, an overloaded API, and a dropped connection that stopped one ticket halfway.",
    "file": "f4ee4edbdadb.wav"
   },
   {
    "t": 70.68,
    "d": 5.36,
    "text": "I made the agent retry those errors and save each finished ticket, so a failure no longer loses work.",
    "file": "1c4ec93f591b.wav"
   }
  ],
  "term": [
   {
    "t": 76.99,
    "d": 4.21,
    "text": "It's two commands: run the agent, then point Trim-T at its traces.",
    "file": "895f4c565d12.wav"
   }
  ],
  "report": [
   {
    "t": 83.99,
    "d": 5.19,
    "text": "The report reads like a receipt: each wasted cost struck out, with the fixed cost beside it.",
    "file": "9b0c9de65a4d.wav"
   }
  ],
  "proof": [
   {
    "t": 97.49,
    "d": 4.76,
    "text": "Then I applied the fixes and reran the same ticket, traced again in neatlogs.",
    "file": "c2efa360a181.wav"
   },
   {
    "t": 102.47,
    "d": 4.5,
    "text": "It came out 74% cheaper, and a check confirmed the answer stayed the same.",
    "file": "acb326878f16.wav"
   }
  ],
  "entire": [
   {
    "t": 107.92,
    "d": 3.94,
    "text": "I built Trim-T with Claude Code, and Entire recorded every session.",
    "file": "058d1868063a.wav"
   },
   {
    "t": 112.08,
    "d": 5.47,
    "text": "Each commit links to the conversation behind it as a checkpoint, so anyone can see why the code changed.",
    "file": "cf11edd91a2d.wav"
   }
  ],
  "cfo": [
   {
    "t": 118.5,
    "d": 6.28,
    "text": "For the business side, I used cfo.ai to plan pricing, costs and runway over two years.",
    "file": "f62435f3e45e.wav"
   },
   {
    "t": 125.0,
    "d": 6.15,
    "text": "A free tier converts to paid Pro and Team plans. Trim-T's own model cost is under a tenth of a cent per run.",
    "file": "6530baa89384.wav"
   }
  ],
  "end": [
   {
    "t": 132.1,
    "d": 2.87,
    "text": "Trim-T. Trim the tokens, keep the answers.",
    "file": "1f2a682db4bd.wav"
   }
  ]
 },
 "premium": "gemini-3.8-flash",
 "cheap": "gemini-3.1-flash-lite",
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
   "short": "Simple steps on the premium model",
   "now": "$0.01692",
   "after": "$0.00303",
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
   "short": "The same big prompt, resent every call",
   "now": "$0.00989",
   "after": "$0.00247",
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
   "short": "The same request, made twice",
   "now": "$0.00317",
   "after": "$0.00000",
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
 "n_measured": 1,
 "run_id": "wasteful-20261012-081021-q1",
 "calls": [
  {
   "step": "classify_intent",
   "model": "gemini-3.8-flash",
   "inp": 2277,
   "out": 283,
   "think": 282,
   "ms": 23951,
   "cost": "$0.00277"
  },
  {
   "step": "extract_keywords",
   "model": "gemini-3.8-flash",
   "inp": 2257,
   "out": 403,
   "think": 384,
   "ms": 25287,
   "cost": "$0.00320"
  },
  {
   "step": "draft_answer",
   "model": "gemini-3.8-flash",
   "inp": 2271,
   "out": 704,
   "think": 598,
   "ms": 38262,
   "cost": "$0.00434"
  },
  {
   "step": "extract_keywords",
   "model": "gemini-3.8-flash",
   "inp": 2257,
   "out": 394,
   "think": 375,
   "ms": 17166,
   "cost": "$0.00317"
  },
  {
   "step": "check_answer",
   "model": "gemini-3.8-flash",
   "inp": 2394,
   "out": 604,
   "think": 573,
   "ms": 31217,
   "cost": "$0.00406"
  },
  {
   "step": "summarise_ticket",
   "model": "gemini-3.8-flash",
   "inp": 2374,
   "out": 516,
   "think": 493,
   "ms": 13992,
   "cost": "$0.00372"
  }
 ],
 "ticket_cost": "$0.02126",
 "ticket_per1k": "$21.26",
 "failures": [
  {
   "code": "429",
   "label": "Rate limit and daily quota",
   "n": 8,
   "fix": "Retry with backoff; budget the quota"
  },
  {
   "code": "503",
   "label": "Model overloaded",
   "n": 9,
   "fix": "Retry with backoff"
  },
  {
   "code": "SSL",
   "label": "Dropped connection",
   "n": 2,
   "fix": "Retry, and save each finished ticket"
  }
 ],
 "checkpoints": [
  {
   "id": "01M4R48HXEJB0VGBD3CJVFWHB5",
   "sha": "b341f7a",
   "msg": "Untrack local preview config"
  },
  {
   "id": "01M4QHHRFX0EMN4JB00A5CW2HC",
   "sha": "bc3f10d",
   "msg": "Add real demo traces, report and explainer video"
  },
  {
   "id": "01M4NEX2193RJ28AW12VZZSM30",
   "sha": "0f72e01",
   "msg": "Build Trim-T: detectors, report, demo agent"
  },
  {
   "id": "01M4NA6ST98QCS00WGJP94WMN7",
   "sha": "7ceace6",
   "msg": "Switch demo from OpenAI to Gemini 3.8 Flash"
  }
 ],
 "neatlogs_shots": [],
 "cfo_shots": [
  "cfo_plan.png"
 ],
 "entire_shots": []
};
