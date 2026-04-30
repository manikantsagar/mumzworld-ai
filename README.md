# Mumzworld Return Reason Classifier

> **Track A — AI Engineering Intern submission**
> Classifies free-text customer return reasons into `refund`, `exchange`, `store_credit`, or `escalate`, with reasoning, confidence score, and a CS agent hint — in English and Arabic.

---

## One-paragraph summary

Mumzworld's customer service team handles thousands of return requests in English and Arabic. Agents must read each free-text reason and manually decide the resolution path — a slow, inconsistent process that is a natural bottleneck for scale. This tool classifies return reasons automatically, surfaces a confidence score, flags uncertainty for human review, and always explains its reasoning in the customer's own language. The escalate bucket is specifically calibrated for health/safety signals, legal threats, and fraud allegations — the cases where wrong auto-classification causes real harm.

---

## Setup — under 5 minutes from clone to first output

```bash
git clone https://github.com/YOUR_USERNAME/mumzworld-return-classifier
cd mumzworld-return-classifier

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-...   # Windows: set ANTHROPIC_API_KEY=sk-...
```

### Run the web app

```bash
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) — the UI loads immediately.

### Or use the API directly

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "The item arrived broken. I want a full refund."}'
```

### Run evals

```bash
python eval.py
```

Prints a graded table and saves `eval_results.json`.

---

## Architecture

```
index.html  (single-file UI)
    │  POST /classify
    ▼
main.py     (FastAPI endpoint — catches all exceptions, never 500s)
    │
    ▼
classifier.py  (calls Anthropic API, strips markdown fences, parses JSON)
    │
    ▼
schema.py   (Pydantic models — ClassificationResult, ClassificationResponse)
```

**Why this shape?**

- **Pydantic validation is the safety net.** The model's JSON output is validated against a strict schema before anything touches the caller. If validation fails, `validation_passed: false` and `error` are returned — never a silent pass with empty fields.
- **The endpoint never returns a 5xx.** Failures surface in the response body so the caller can decide what to do (e.g. route to human agent). This is intentional: a CS tool that crashes is worse than one that says "I'm not sure."
- **Single file frontend.** No build step, no npm. The UI is served directly by FastAPI via `FileResponse`. This keeps the demo runnable in one command.

---

## Model choice

| Option | Why considered | Why chosen / rejected |
|---|---|---|
| `claude-haiku-4-5` | Fast, cheap, multilingual | **Chosen as default.** Sufficient for classification; ~10x cheaper than Sonnet. |
| `claude-sonnet-4-6` | Higher reasoning quality | Available via `CLASSIFIER_MODEL=claude-sonnet-4-6` env var for production. |
| Open-weights (Llama 3, Qwen) | Free via OpenRouter | Rejected — Arabic quality and instruction-following on structured output is significantly weaker for this use case. |

Set `CLASSIFIER_MODEL=claude-sonnet-4-6` in your environment to upgrade.

---

## Evals

### Rubric

| Criterion | Pass condition |
|---|---|
| Category accuracy | Predicted category matches ground truth label |
| Language detection | `language_detected` matches expected language |
| Confidence calibration | Low confidence (< 0.6) on ambiguous/adversarial inputs |
| Uncertainty flagging | `uncertainty_flag: true` on adversarial/ambiguous inputs |
| Reasoning language | Reasoning text must be in the same language as the input |

### Test cases (15 total)

| ID | Difficulty | Expected | Note |
|---|---|---|---|
| 1 | easy | refund | Clear damaged product, English |
| 2 | easy | exchange | Wrong size, English |
| 3 | easy | store_credit | Explicit credit request, English |
| 4 | easy | escalate | Health emergency + legal threat |
| 5 | easy | refund | Arabic — damaged, wants refund |
| 6 | easy | exchange | Arabic — wrong size |
| 7 | easy | store_credit | Arabic — prefers credit |
| 8 | easy | escalate | Arabic — expired product, sick child |
| 9 | ambiguous | refund | "I just don't like it" — vague |
| 10 | medium | escalate | Partial order, needs investigation |
| 11 | adversarial | escalate | Customer cancels return — no intent |
| 12 | medium | escalate | Arabic — fake halal certification fraud |
| 13 | adversarial | escalate | Emoji-only input |
| 14 | medium | exchange | Mentions both exchange and credit |
| 15 | medium | exchange | Wants different product as gift |

### Scores (run `python eval.py` to reproduce)

| Metric | Score |
|---|---|
| Category accuracy | 14/15 = 93.3% |
| Language accuracy | 15/15 = 100% |
| Easy cases | 8/8 |
| Medium cases | 3/4 |
| Ambiguous cases | 1/1 |
| Adversarial cases | 2/2 |

**Known failure mode:** Case 14 (customer mentions both exchange and store_credit). The model sometimes picks store_credit because it appears later and the tone is more decisive. Fixed in production by adding an explicit tie-breaking rule in the system prompt: *"When the customer lists multiple resolution types, prefer the first one mentioned."*

---

## Uncertainty handling

The model is explicitly instructed to:

- Set `uncertainty_flag: true` when intent is genuinely ambiguous
- Set confidence < 0.6 on adversarial or vague inputs
- Prefer `escalate` over guessing a resolution type when unsure
- Never invent information not in the input
- Return `escalate` when no actual return intent is detected

The UI surfaces `uncertainty_flag` as a visible warning banner so CS agents know to review before acting.

---

## Tradeoffs

### Why this problem

Return classification is a real, high-volume Mumzworld operation. Misclassification causes either customer friction (wrong resolution offered) or financial risk (auto-refunding something that should be escalated for safety). It maps cleanly to the required AI engineering techniques: structured output with schema validation, multilingual input, confidence calibration, and evals with named failure modes.

Rejected alternatives:
- **Gift Finder** — higher novelty but harder to eval rigorously (subjective quality).
- **Moms Verdict** — interesting but the eval story is weak ("is this a good summary?" is fuzzy).

### What I cut

- **Streaming responses** — not needed for a classification task; adds complexity.
- **Database / history** — out of scope for a prototype; a production version would log every classification for audit and retraining.
- **Fine-tuning** — not justified yet; the base model with a strong system prompt achieves >90% accuracy on this task. Fine-tuning would be the next step after collecting 1000+ labelled real examples.
- **Auth on the API** — CS tool would need auth in production; omitted to keep setup under 5 minutes.

### What I would build next

1. **Confidence threshold routing** — auto-resolve high-confidence refund/exchange/store_credit; always route escalate and low-confidence to a human queue.
2. **Audit log** — every classification stored with input, output, confidence, and agent override for retraining.
3. **Active learning loop** — when an agent overrides the model, flag that case for labelling and retrain quarterly.
4. **Streaming UI** — show reasoning tokens as they arrive for faster perceived latency.

---

## Tooling

| Tool | Role |
|---|---|
| **Claude (claude.ai)** | Architecture design, system prompt iteration, README drafting |
| **Anthropic API (claude-haiku-4-5)** | Classification inference at runtime |
| **FastAPI + Pydantic** | API layer and schema validation |
| **Uvicorn** | ASGI server |

**How I used Claude:**
- Iterated the system prompt ~4 times, each time testing against the adversarial cases (emoji-only, "I changed my mind", fake halal) to close escape hatches.
- The key prompt engineering insight was making `escalate` an explicit catch-all for anything that *could* cause harm if auto-resolved, rather than a last resort. This fixed the sick-child and fraud cases immediately.
- Pydantic schema was written first (schema-first design) so the model's output had a concrete target to validate against.
- Where the agent suggested padding the reasoning field with generic text, I overruled it and added an explicit instruction: *"reasoning must reference specific words from the input."*

---

## Time log

| Phase | Time |
|---|---|
| Problem scoping and schema design | 45 min |
| System prompt iteration (4 rounds) | 60 min |
| classifier.py + main.py | 30 min |
| Frontend UI | 45 min |
| Test cases (15) + eval runner | 60 min |
| README + EVALS.md | 40 min |
| **Total** | **~5 hrs** |
