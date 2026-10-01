# Jev code-along (30 min) — lesson guide

We're live-coding in front of an audience of analysts and some software engineers, many new to Jev. Keep each code cell short and readable, show outputs as small tables, and **do arithmetic, dates and counting in Python, never in Jev**. Use synthetic data only. Report measured timings, not claimed ones.

**Docs:** https://docs.typesafe.ai/llms.txt (index) · primitives https://docs.typesafe.ai/primitives.md · confidence https://docs.typesafe.ai/confidence.md · jaggedness https://docs.typesafe.ai/model-jaggedness/jev-1.13.md · Python SDK https://docs.typesafe.ai/sdk/python.md · composite scoring https://docs.typesafe.ai/patterns/composite-scoring.md · intent routing https://docs.typesafe.ai/patterns/intent-routing.md

**API basics:** `from typesafe_sdk import TypeSafeClient, Noul, Choice, Score`. Call `client.system_one(state=..., questions={...})`; the response has `.answers`, `.usage.input_tokens` and `.model`. A Noul returns `noul` (0–1). Choice and Score return `choice`/`score`, `probabilities` and `confidence`. Price is $0.042 per million input tokens and output is free. Limits: 64k tokens per request, 32k for the state plus the longest question.

## Flow
1. **Hello Noul (3 min)**: one support ticket, one yes/no question. Show the raw response, then write a tiny `ask(state, **questions) -> DataFrame` helper.
2. **All three primitives (4 min)**: Choice (department), Score (frustration) and Noul (urgent) on one ticket. Edit the ticket live until it's ambiguous and watch confidence drop.
3. **Fan-out (4 min)**: a long public document (~10–20k tokens). Time 1 question vs 50 and compare `input_tokens`. The point: you pay for the document once, and latency stays flat.
4. **Break it (5 min)**:
   - Count fruit in a 24-item list with one Choice, vs one Noul per item summed in Python.
   - Hard date questions, like "within 7 days of the end of Q3?"
   - A question and its negation: add the two probabilities and show they don't sum to 1.
   - The point: probabilities near 0.5 are Jev saying "not sure".
5. **Routing myth (4 min)**: 8 mixed LLM requests.
   - Ask a Choice "which model: small/medium/frontier?" It answers confidently, but there's no ground truth to check it against.
   - Ask feature Nouls instead: asks for slides, contains code, needs current info. Route with a dict in Python.
   - Mention Theo's result: as a router, Jev matched GPT-6 Astra low on score but was about 4× slower.
6. **Credit scorecard on free text (8 min)**:
   - About 8 synthetic applicant narratives (hardship letters, employment notes), with income and debts kept as separate numeric fields.
   - Questions: employment stability (Score 0–3), irregular income, other borrowing, payday loans, difficulty paying bills, specific loan purpose (Nouls), loan purpose (Choice).
   - Combine with weights in Python to get points plus the top 3 negative reason codes. Flag any Noul between 0.3 and 0.7 for human review.
   - Mini-eval: hand-label each question and report accuracy.
   - Bias check: swap the applicant's name or gender and diff the outputs.
7. **Wrap (2 min)**: total `input_tokens` × price for the whole session.
