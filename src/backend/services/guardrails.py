OFF_TOPIC_KEYWORDS = [
    "joke", "story", "movie", "weather", "poem", "recipe", "song",
    "capital of", "who is the president", "translate", "write me a",
    "what is 2+2", "sports", "news", "stock price", "celebrity",
]

O2C_KEYWORDS = [
    "sales order", "delivery", "billing", "invoice", "payment",
    "journal", "customer", "product", "plant", "trace", "flow",
    "order", "dispatch", "shipment", "ledger", "o2c",
]


def is_valid_query(query: str) -> bool:
    q = query.lower()
    if any(k in q for k in OFF_TOPIC_KEYWORDS):
        return False
    return True


def guardrail_response() -> str:
    return (
        "This system is designed to answer questions related to the "
        "SAP Order-to-Cash dataset only. Please ask about sales orders, "
        "deliveries, billing, payments, customers, or products."
    )