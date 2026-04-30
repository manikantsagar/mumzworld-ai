import json
import os
from anthropic import Anthropic
from schema import ClassificationResult

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Haiku is fast and cheap; swap to claude-sonnet-4-6 for higher accuracy if needed
MODEL = os.environ.get("CLASSIFIER_MODEL", "claude-haiku-4-5-20251001")

SYSTEM_PROMPT = """You are a return-reason classifier for Mumzworld, the largest e-commerce platform
for mothers in the Middle East. Customers write return reasons in English or Arabic.

Your job: read the free-text return reason and output a single JSON object — nothing else.
No prose. No markdown fences. No explanation outside the JSON.

CATEGORIES (pick exactly one):
- "refund"       : Customer wants money back to original payment method.
- "exchange"     : Customer wants a different size, colour, or variant of the same or similar product.
- "store_credit" : Customer accepts credit to spend on a future Mumzworld order.
- "escalate"     : Use when you detect ANY of the following:
                    • Safety/health concern (expired product, sick child, allergic reaction)
                    • Legal threat or mention of regulatory bodies
                    • Fraud or mislabelling allegation (e.g. fake halal certification)
                    • Abusive, threatening, or distressing language
                    • Partial/missing order (requires investigation before resolution)
                    • Genuine ambiguity that no CS rule can resolve without human judgment

RULES:
1. Detect the language of the input (en or ar).
   Write the "reasoning" field in the SAME language as the input — never translate it.
2. "suggested_response_hint" is ALWAYS in English, regardless of input language.
   It is a single actionable sentence for the customer service agent.
3. If the intent is ambiguous or the text is too short to be sure:
   - Lower confidence below 0.6
   - Set uncertainty_flag to true
   - Prefer "escalate" over guessing a resolution type
4. Never invent information not present in the text.
5. If the text contains no actual return intent (e.g. customer changed their mind),
   use "escalate" with a note in suggested_response_hint.

OUTPUT FORMAT — strict JSON, no extra text:
{
  "category": "refund" | "exchange" | "store_credit" | "escalate",
  "confidence": <float 0.0–1.0>,
  "reasoning": "<explanation in same language as input>",
  "language_detected": "en" | "ar",
  "uncertainty_flag": <true | false>,
  "suggested_response_hint": "<one English sentence for CS agent>"
}"""


def classify(text: str) -> ClassificationResult:
    """
    Classify a free-text return reason.
    Returns a validated ClassificationResult or raises on schema failure.
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )

    raw = response.content[0].text.strip()

    # Defensively strip markdown fences — the model sometimes adds them
    # despite instructions, especially on edge-case inputs.
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip()

    data = json.loads(raw)          # Raises json.JSONDecodeError on malformed output
    return ClassificationResult(**data)   # Raises ValidationError on schema mismatch
