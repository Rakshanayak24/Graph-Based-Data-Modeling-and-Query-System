# Dodge AI — O2C Graph Intelligence
> **Forward Deployed Engineer Assignment**

**Live Demo:** `http://localhost:3000` (run locally per setup below)
**Stack:** React + Cytoscape.js · FastAPI · NetworkX · Groq LLM

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  React Frontend (Cytoscape fcose)                        │
│  • Full graph visualization on load                      │
│  • Light/Dark theme, Minimize, Granular Overlay toggle   │
│  • Node detail cards with all metadata on click          │
│  • Dynamic chips with real document IDs from the graph   │
└────────────────────┬────────────────────────────────────┘
                     │ REST (JSON)
┌────────────────────▼────────────────────────────────────┐
│  FastAPI Backend                                         │
│  GET  /graph/full  → all nodes + edges for canvas       │
│  POST /query       → NL query → graph/text answer       │
│  GET  /health      → node/edge count                    │
└─────┬──────────────────────────────┬────────────────────┘
      │                              │
┌─────▼──────────┐        ┌─────────▼──────────────────┐
│  GraphEngine   │        │  QueryEngine               │
│  NetworkX      │        │  Groq llama-3.1-8b-instant │
│  DiGraph       │        │  Intent classifier only    │
│  In-memory     │        │  → routes to GraphEngine   │
└────────────────┘        └────────────────────────────┘
```

---

## 1. Code Quality & Architecture

**Structure:**
```
src/
├── backend/
│   ├── main.py                    # FastAPI app, singleton engine, 3 endpoints
│   └── services/
│       ├── graph_engine.py        # NetworkX graph, all query methods
│       ├── query_engine.py        # LLM classifier + keyword pre-check + router
│       └── guardrails.py          # Keyword blocklist (imported by query_engine)
└── frontend/
    ├── package.json
    └── src/
        ├── App.js                 # Complete React app, theming, Cytoscape
        └── index.js
```

**Principles applied:**
- Single responsibility: each file has one job
- Singleton pattern: GraphEngine loaded once at startup, shared across requests
- Separation of concerns: LLM classification is completely decoupled from graph logic
- Defensive coding: edge safety filter in `/query`, error boundaries in frontend

---

## 2. Graph Modelling

All 19 JSONL folders unified into one directed graph. Every node carries **all source metadata fields**.

```
Customer ──placed_order──▶ SalesOrder ──has_item──▶ SalesOrderItem
                                │                        │
                          delivered_via          references_product
                                ▼                        ▼
                           Delivery ──ships_from──▶ Plant
                                │
                           billed_via
                                ▼
                           Billing ──billed_product──▶ Product
                                │
                          journal_entry
                                ▼
                          JournalEntry
                                │
                      cleared_by_payment
                                ▼
                            Payment
```

**Node types:** `sales_order`, `sales_order_item`, `delivery`, `billing`, `journal`, `payment`, `customer`, `product`, `plant`, `address`

**Edge types:** `placed_order`, `has_item`, `delivered_via`, `ships_from_plant`, `billed_via`, `billed_product`, `journal_entry`, `cleared_by_payment`, `has_address`, `references_product`

**Result:** ~788 nodes, ~4245 edges loaded from all 19 folders.

---

## 3. Database / Storage Choice

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Graph store** | NetworkX DiGraph (in-memory) | Sub-millisecond BFS/DFS. Dataset (~800 nodes) fits in RAM. No external process needed. Full Python control of graph algorithms. |
| **Source data** | JSONL files, read once at startup | No ETL pipeline needed. Load → parse → graph in one pass. |
| **Why not Neo4j/ArangoDB** | External process, Cypher query language overhead, deployment complexity — unjustified for this dataset size. |
| **Why not SQL** | O2C workflows are path queries (trace a billing doc through 5 hops). SQL needs 5 JOINs; graph traversal is 5 pointer dereferences. |

---

## 4. LLM Integration & Prompting

**Model:** Groq `llama-3.1-8b-instant` — free tier, ~200ms latency

**Strategy: LLM as classifier only, never as answerer**

```
User query
    │
    ▼
Keyword pre-check (deterministic, ~0ms)
    │  if keyword match → route immediately (no LLM call)
    ▼
LLM classification (structured JSON output)
    │  intent + parameters
    ▼
GraphEngine method call (deterministic)
    │  data-backed result
    ▼
Response to user
```

**Why this approach:**
- Zero hallucination risk — LLM never generates the answer
- Deterministic outputs — same query always returns same graph data
- Fast — keyword pre-check avoids LLM call for common queries
- Reliable — LLM only needs to do easy classification, not complex reasoning

**LLM Prompt design:**
```json
{
  "intent": "trace | top_products | broken_flows | customer | lookup_journal | off_topic | unknown",
  "parameters": {
    "document_id": "<ID or null>",
    "customer_id": "<ID or null>",
    "billing_id":  "<ID for journal lookup or null>"
  }
}
```

System prompt includes concrete examples for each intent class, strict JSON-only instruction, and explicit priority rules (lookup_journal > trace when "journal" keyword present).

**Natural language to structured query examples:**

| NL Query | Intent | Graph Method Called |
|----------|--------|---------------------|
| "trace billing 90504204" | `trace` | `engine.trace("90504204")` |
| "find journal entry 90504248" | `lookup_journal` | `engine.lookup_journal_for_billing("90504248")` |
| "which products have most billing" | `top_products` | `engine.get_top_products()` |
| "show incomplete flows" | `broken_flows` | `engine.get_broken_flows()` |
| "show customer 310000108" | `customer` | `engine.get_customer_info("310000108")` |

---

## 5. Guardrails

**Two-layer defense:**

**Layer 1 — Keyword blocklist (pre-LLM, 0ms):**
```python
_OFF_TOPIC_HARD = [
    "joke", "poem", "story", "weather", "recipe", "song lyrics",
    "movie plot", "capital of", "who invented", "write me a",
    "translate this", "sports score", "celebrity", "horoscope",
]
# Fires BEFORE any LLM call
```

**Layer 2 — LLM off_topic classification:**
```
If query is not in blocklist but LLM classifies intent = "off_topic"
→ Return domain restriction message
```

**Layer 3 — Intent routing:**
Only 6 known intents execute code. Unknown/off_topic → safe help message.

**Layer 4 — Edge safety:**
`/query` strips edges whose source/target nodes don't exist in the response before sending to frontend.

**Example responses:**
- "tell me a joke" → *"This system is designed to answer questions related to the SAP Order-to-Cash dataset only."*
- "what is the capital of France" → Same
- "write me a poem about supply chains" → Same (blocked by "poem" keyword before LLM)

---

## Bonus Features Implemented

| Feature | Implementation |
|---------|---------------|
| ✅ NL → structured graph query | LLM intent classifier → typed graph methods |
| ✅ Node highlighting | `focusNode()` animates to + highlights queried node |
| ✅ Conversation memory | Full message history maintained in React state |
| ✅ Dynamic suggestion chips | Chip IDs derived from real graph data at load time |
| ✅ Dark/Light theme | Full dual-theme system applied to all UI + Cytoscape canvas |
| ✅ Granular overlay toggle | Switches between tiny-dot mode (dense web) and labeled node mode |
| ✅ Journal lookup intent | Handles "find journal entry for billing X" → walks full chain |
| ✅ Rich node cards | All metadata fields shown on click, connections count |
| ✅ Minimize panel | Graph collapses with animation, ▶ tab to restore |

---

## Example Queries

| Query | Response |
|-------|----------|
| `top products` | Top 15 products by billing document count, graph view |
| `broken flows` | All SO→Delivery→Billing gaps highlighted as missing nodes |
| `trace billing 90504204` | Full O2C trace: Customer→SO→Delivery→Billing→Journal→Payment |
| `show customer 310000108` | Customer node + all linked orders and addresses |
| `find journal entry 90504248` | Journal entry `9400000249` highlighted, full chain shown |
| `tell me a joke` | Guardrail: domain restriction message |

---

## Setup

### Backend
```bash
cd src/backend
pip install fastapi uvicorn networkx pandas groq

# Set your Groq API key
export GROQ_API_KEY=gsk_xxx   # or paste directly in query_engine.py

uvicorn main:app --reload
# → http://127.0.0.1:8000
# → http://127.0.0.1:8000/health  (check node/edge count)
# → http://127.0.0.1:8000/docs    (API explorer)
```

### Frontend
```bash
cd src/frontend
npm install
npm install cytoscape-fcose   # required for force-directed layout
npm start
# → http://localhost:3000
```

> **Note:** Update `DATA_PATH` in `services/graph_engine.py` to your local path before running.

---

## Key Engineering Decisions Summary

| Decision | What | Why |
|----------|------|-----|
| Graph over SQL | NetworkX DiGraph | Path queries (BFS/DFS) are O(V+E); SQL JOINs are O(n²) |
| LLM as classifier | Intent JSON only | Zero hallucination; deterministic results |
| Keyword pre-check | Before LLM | 100% reliable for common patterns; saves API calls |
| fcose layout | Force-directed | Organic clustering shows real graph topology |
| In-memory | No external DB | Sub-ms queries; fits dataset; simpler deployment |
| Singleton engine | Loaded at startup | One graph instance shared; no per-request rebuild |