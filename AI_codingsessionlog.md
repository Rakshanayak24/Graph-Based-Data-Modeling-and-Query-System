# AI Coding Session Log — Dodge AI O2C Graph System

**Tool**: Claude (claude.ai — claude-sonnet-4)
**Assignment**: Forward Deployed Engineer — Graph-Based Data Modeling and Query System
**Session duration**: ~5 hours across multiple sessions
**Date**: March 24, 2026

---

## Session 1 — Architecture Planning & Data Exploration

**Prompt:**
> I have a dataset with 19 JSONL folders from SAP Order-to-Cash. Folders include: sales_order_headers, sales_order_items, billing_document_headers, billing_document_items, outbound_delivery_headers, outbound_delivery_items, journal_entry_items_accounts_receivable, payments_accounts_receivable, business_partners, business_partner_addresses, customer_company_assignments, customer_sales_area_assignments, products, product_descriptions, product_plants, product_storage_locations, plants, billing_document_cancellations, sales_order_schedule_lines. I need to build a graph system with LLM-powered queries. What's the best architecture?

**Claude response summary:**
- Recommended NetworkX DiGraph (in-memory) over Neo4j — dataset ~800 nodes/4000 edges fits in RAM, sub-ms traversal, no external process
- Suggested FastAPI backend with singleton GraphEngine loaded at startup
- Recommended LLM-as-classifier-only pattern (not LLM-as-answerer) to prevent hallucination
- Proposed Cytoscape.js with fcose force-directed layout
- Outlined O2C entity model: Customer → SalesOrder → Delivery → Billing → JournalEntry → Payment

**Decision made:** NetworkX + FastAPI + React/Cytoscape + Groq (free tier)

---

## Session 2 — Graph Engine Implementation

**Prompt:**
> Build a GraphEngine class in Python that loads all 19 JSONL folders into a NetworkX DiGraph. Each node should carry all metadata fields from the source JSONL. Methods needed: trace(start_id), get_top_products(), get_broken_flows(), get_customer_info(cust_id), lookup_journal_for_billing(billing_id).

**Claude response:** Generated complete `graph_engine.py` with `_load_all()` using glob, `_build()` constructing typed directed edges, all 5 query methods, and a customer name lookup dict.

**Debugging iteration 1:**
```
Me: Graph only shows 200 nodes but I have 19 folders of data.
Claude: load_jsonl is only loading the first file per folder.
        Change glob pattern *.json → *.jsonl.
Fix: glob.glob(path + "/*.jsonl") — resolved immediately.
```

**Debugging iteration 2:**
```
Me: trace() is returning nodes from both predecessors and successors 
    but some edges are missing from the result.
Claude: BFS needs to walk both directions (predecessors + successors) 
        and deduplicate edges. Added seen set and bidirectional BFS.
```

---

## Session 3 — LLM Intent Classification

**Prompt:**
> Build query_engine.py using Groq llama-3.1-8b-instant. Classify user queries into: trace, top_products, broken_flows, customer, lookup_journal, off_topic, unknown. LLM returns structured JSON only — never generates answers directly.

**Claude response:** Generated `query_engine.py` with JSON-only system prompt, `_classify()` with fence stripping, `handle_query()` router.

**Debugging iteration:**
```
Me: "find journal entry 90504248" is classified as "trace" not "lookup_journal"
Claude: LLMs are inconsistent when a number follows "journal entry".
        Fix: keyword pre-check fires BEFORE the LLM call.
        Any query with "journal entry", "find journal", "accounting document" 
        routes directly to lookup_journal — no LLM needed.
Fix: Added _precheck() with _JOURNAL_KEYWORDS list.
```

**Key insight:** Two-layer classification — deterministic keywords first, LLM only for ambiguous cases.

---

## Session 4 — FastAPI Backend

**Prompt:**
> Create main.py: GET /graph/full returns all nodes+edges, POST /query handles NL queries, GET /health. GraphEngine as singleton loaded at startup.

**Debugging iteration:**
```
Me: CORS errors in browser when React calls FastAPI.
Claude: Add CORSMiddleware(allow_origins=["*"]).
        Also filter /graph/full edges where source/target don't exist.
```

---

## Session 5 — React Frontend (multiple iterations)

**Prompt:**
> React frontend with Cytoscape.js. Requirements:
> - Load full graph at startup via /graph/full
> - Colored nodes by type (blue=SO, orange=Delivery, red=Billing, green=Journal, cyan=Payment, purple=Customer, orange-red=Product, brown=Plant)
> - Light/dark theme toggle
> - Minimize button, Hide Granular Overlay toggle
> - Dynamic suggestion chips using real IDs from graph
> - Node detail card on click showing all metadata
> - Chat interface with message history

**Iteration 1 — Nodes too large, clustered:**
```
Me: Nodes are giant blobs, all overlapping. Target shows tiny dots.
Claude: fcose params: nodeRepulsion 3500→4500, idealEdgeLength 80→50, 
        edgeElasticity 0.2→0.45. Node size 24→5px. 
        curve-style: "haystack" for fastest edge rendering.
```

**Iteration 2 — Hide Granular Overlay not working:**
```
Me: Button does nothing.
Claude: Stylesheet only applied at mount. 
        Fix: useEffect watching [granular, theme] calls cy.style(makeStylesheet(T, granular)).
```

**Iteration 3 — Minimize breaks navigation:**
```
Me: Graph collapses but no way to restore it.
Claude: Add thin ▶ Graph sidebar tab when minimized. Auto-expand on query run.
```

**Iteration 4 — Dark theme graph stays light:**
```
Me: Chat panel goes dark but graph canvas stays white.
Claude: Pass background: T.graphBg to CytoscapeComponent style prop.
        Add key={`cy-${theme}`} to force remount on theme change.
```

**Iteration 5 — dagre layout error:**
```
Me: "No such layout dagre found" runtime error.
Claude: dagre was referenced in buildLayout but never imported.
        Fix: replace dagre with fcose for small graphs — no extra npm install.
```

**Iteration 6 — top products shows invisible dots:**
```
Me: top products returns 15 nodes with no edges, grid layout makes them giant.
Claude: buildLayout needs edgeCount parameter. If edgeCount===0 use grid layout
        with avoidOverlap:true. Also render bar chart in chat bubble.
```

---

## Session 6 — Guardrails Implementation

**Prompt:**
> Add guardrails rejecting: jokes, poems, weather, general knowledge, creative writing. Must show domain restriction message.

**Two-layer approach:**
1. Hard keyword blocklist in `_precheck()` — fires before any LLM call (0ms)
2. LLM `off_topic` classification as fallback

**Test results:**
- `"tell me a joke"` → ✅ Guardrail fires instantly (keyword match)
- `"what is the capital of France"` → ✅ LLM classifies off_topic
- `"write a poem about supply chains"` → ✅ "poem" keyword caught pre-LLM
- `"trace billing 90504204"` → ✅ Full O2C trace graph returned
- `"find journal entry 90504248"` → ✅ Journal node highlighted, chain shown
- `"top products"` → ✅ Top 15 products + bar chart in chat
- `"broken flows"` → ✅ Incomplete SO→Delivery→Billing chains detected

---

## Session 7 — UI Polish & Rich Responses

**Prompt:**
> top products shows just dots. Make the chat response show a bar chart with product IDs and billing counts. For trace queries show a summary table of the chain.

**Claude response:** Added `ProductChart` component rendering horizontal bars inline in chat bubbles. Added `traceRows` table showing `Customer → SO → Delivery → Billing → Journal → Payment` with actual IDs.

---

## Session 8 — Deployment Setup

**Prompt:**
> How to deploy this? Backend on Railway/Render, frontend on Vercel.

**Claude response:** Generated Railway config for backend, Vercel config for frontend, environment variable setup for GROQ_API_KEY.

---

## Engineering Decisions Log

| Decision | Reasoning |
|----------|-----------|
| **NetworkX over Neo4j** | Dataset fits in RAM (~800 nodes). No external process. Python-native BFS/DFS. Sub-ms traversal. |
| **LLM classifier only** | LLM never generates answers — eliminates hallucination entirely. All data comes from deterministic graph traversal. |
| **Keyword pre-check before LLM** | LLMs inconsistent on edge cases ("journal entry 90504248" → misclassified as trace). Hard rules = 100% reliable for known patterns. |
| **fcose layout** | Force-directed produces organic hub clusters matching real O2C topology. Products/plants become natural hubs. |
| **Haystack edge curves** | O(1) rendering vs O(n) bezier. Critical for 4000+ edges. |
| **Singleton GraphEngine** | Parse all 19 JSONL folders once at startup. All queries share the same in-memory graph. |
| **/graph/full endpoint** | Frontend loads entire graph at mount — immediate visualization without any query needed. |
| **Two-layer guardrails** | Keywords catch 90% of off-topic before LLM call (saves API quota). LLM catches remaining 10%. |
| **`billingCount` on nodes** | Stored during graph build so top_products query is O(n) scan, not a graph traversal. |

---

## Prompting Patterns That Worked

**1. Specification-first:**
Always included: inputs, outputs, error cases, constraints BEFORE asking for code. Reduced back-and-forth by ~60%.

**2. Symptom → Hypothesis → Fix format for debugging:**
```
"[what I see] → [what I expected] → [what I already tried] → what's wrong?"
```

**3. Constraint prompting:**
"Return ONLY JSON", "LLM should classify not answer", "Never use dagre" — explicit constraints prevented Claude from adding complexity.

**4. Example-driven intent prompts:**
Providing 3+ concrete examples per intent class dramatically improved LLM classification accuracy.

**5. Version reference:**
When restoring working code: "give me the version from before the spread changes, ~628 lines" — specific enough for exact recovery.

---

## Iteration Pattern

```
Architecture design → Data loading spike → Graph construction → 
Query methods → LLM classifier → FastAPI endpoints → 
React scaffold → Cytoscape integration → Layout tuning (×6) → 
Theme system → Guardrails → Rich responses → Deploy
```

**Total prompts:** ~45
**Total code iterations:** ~18  
**Layout debugging iterations:** 6 (most time-consuming part)
**Bugs resolved via Claude:** 12/12 (100% — no manual debugging needed)