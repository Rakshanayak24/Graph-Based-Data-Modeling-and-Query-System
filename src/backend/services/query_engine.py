import json
import re
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY",
    "YOUR API"))

_SYSTEM = """
You are a routing agent for a SAP Order-to-Cash (O2C) analytics system.
Return ONLY a valid JSON object — no markdown, no text outside the JSON.

Schema:
{
  "intent": "<intent>",
  "parameters": {
    "document_id": "<any numeric/alphanumeric ID mentioned, or null>",
    "customer_id": "<customer/business partner ID, or null>",
    "billing_id":  "<billing document number when looking up journal, or null>"
  }
}

Intents:
- trace          → trace/follow/lifecycle of a document through SO→Delivery→Billing→Journal
- top_products   → products with most billing/orders/deliveries
- broken_flows   → incomplete, broken, or missing O2C steps
- customer       → specific customer or business partner details
- lookup_journal → find journal entry / accounting document number linked to a billing doc
- unknown        → O2C-related but unclear
- off_topic      → nothing to do with SAP/O2C

Return ONLY the JSON object.
"""


def _extract_id(text: str) -> str | None:
    """Pull the first long numeric ID (7+ digits) from text."""
    nums = re.findall(r'\b\d{7,}\b', text)
    return nums[0] if nums else None


# ── Keyword-based pre-classifier (runs BEFORE LLM, prevents misrouting) ──────
_JOURNAL_KEYWORDS = [
    "journal entry", "journal number", "find journal", "get journal",
    "journal linked", "journal for billing", "journal for",
    "accounting document", "accounting doc", "which journal",
    "what journal", "journal entry number", "journal entry for",
    "find the journal", "linked to this", "linked to billing",
]
_TRACE_KEYWORDS    = ["trace", "follow", "lifecycle", "full flow", "track flow"]
_BROKEN_KEYWORDS   = ["broken", "incomplete", "missing", "not billed", "not delivered", "undelivered", "no delivery", "no billing"]
_TOP_PROD_KEYWORDS = ["top product", "best product", "most billed product", "highest billing product", "products associated"]
_CUSTOMER_KEYWORDS = ["show customer", "customer details", "business partner", "who is customer"]
_OFF_TOPIC_HARD    = ["joke", "poem", "story", "weather", "recipe", "song lyrics", "movie plot",
                       "capital of", "who invented", "write me a", "translate this", "sports score",
                       "celebrity", "horoscope", "what is 2+2"]


def _precheck(query: str) -> dict | None:
    """
    Fast keyword-based routing that fires BEFORE the LLM.
    Returns a classified dict if confident, else None (fall through to LLM).
    """
    q   = query.lower()
    nid = _extract_id(query)

    # Hard off-topic block
    if any(k in q for k in _OFF_TOPIC_HARD):
        return {"intent": "off_topic", "parameters": {}}

    # Journal lookup — highest priority keyword match
    if any(k in q for k in _JOURNAL_KEYWORDS):
        return {"intent": "lookup_journal",
                "parameters": {"billing_id": nid, "document_id": nid}}

    # Broken flows
    if any(k in q for k in _BROKEN_KEYWORDS):
        return {"intent": "broken_flows", "parameters": {}}

    # Top products
    if any(k in q for k in _TOP_PROD_KEYWORDS):
        return {"intent": "top_products", "parameters": {}}

    # Customer
    if any(k in q for k in _CUSTOMER_KEYWORDS):
        return {"intent": "customer", "parameters": {"customer_id": nid}}

    # Explicit trace
    if any(k in q for k in _TRACE_KEYWORDS) and nid:
        return {"intent": "trace", "parameters": {"document_id": nid}}

    return None  # fall through to LLM


def _llm_classify(query: str) -> dict:
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": query},
            ],
            temperature=0,
            max_tokens=200,
        )
        raw = res.choices[0].message.content.strip()
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        result = json.loads(raw)
        # Ensure billing_id is set for lookup_journal
        p = result.get("parameters", {})
        if result.get("intent") == "lookup_journal" and not p.get("billing_id"):
            p["billing_id"] = p.get("document_id") or _extract_id(query)
            result["parameters"] = p
        return result
    except Exception as e:
        print(f"⚠️  LLM error: {e}")
        # Rule-based fallback
        nid = _extract_id(query)
        q   = query.lower()
        if nid and any(k in q for k in ["journal", "accounting"]):
            return {"intent": "lookup_journal", "parameters": {"billing_id": nid, "document_id": nid}}
        if nid:
            return {"intent": "trace", "parameters": {"document_id": nid}}
        return {"intent": "unknown", "parameters": {}}


def _classify(query: str) -> dict:
    # 1. Fast keyword pre-check
    pre = _precheck(query)
    if pre is not None:
        print(f"✅ Pre-check classified: {pre['intent']}")
        return pre
    # 2. LLM classification
    result = _llm_classify(query)
    print(f"🤖 LLM classified: {result.get('intent')} | params: {result.get('parameters')}")
    return result


# ── Main handler ─────────────────────────────────────────────────────────────
def handle_query(query: str, engine) -> dict:
    j       = _classify(query)
    intent  = j.get("intent", "unknown")
    p       = j.get("parameters", {})
    doc_id  = p.get("document_id")
    cust_id = p.get("customer_id")
    bil_id  = p.get("billing_id") or doc_id

    # ── Off-topic guardrail ───────────────────────────────────────────────
    if intent == "off_topic":
        return {
            "type": "text",
            "explanation": (
                "This system is designed to answer questions related to the "
                "SAP Order-to-Cash dataset only. Please ask about sales orders, "
                "deliveries, billing documents, journal entries, payments, customers, or products."
            ),
        }

    # ── Route to engine ───────────────────────────────────────────────────
    if intent == "lookup_journal":
        if bil_id:
            return engine.lookup_journal_for_billing(str(bil_id))
        return {
            "type": "text",
            "explanation": "Please provide a billing document number (e.g. 'find journal entry for 90504248').",
        }

    if intent == "trace":
        if doc_id:
            return engine.trace(str(doc_id))
        return {
            "type": "text",
            "explanation": "Please specify a document ID to trace (e.g. 'trace billing 90504204').",
        }

    if intent == "top_products":
        return engine.get_top_products()

    if intent == "broken_flows":
        return engine.get_broken_flows()

    if intent == "customer":
        if cust_id:
            return engine.get_customer_info(str(cust_id))
        return {
            "type": "text",
            "explanation": "Please provide a customer ID (e.g. 'show customer 310000108').",
        }

    # ── Unknown O2C ───────────────────────────────────────────────────────
    return {
        "type": "text",
        "explanation": (
            "I can help with:\n"
            "• Trace a document — 'trace billing 90504204'\n"
            "• Top products — 'top products'\n"
            "• Broken flows — 'broken flows'\n"
            "• Customer details — 'show customer 310000108'\n"
            "• Journal lookup — 'find journal entry for 90504248'"
        ),
    }