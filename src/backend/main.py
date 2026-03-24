from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from services.graph_engine import GraphEngine
from services.query_engine  import handle_query

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Dodge AI — O2C Graph", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("o2c")

# ── Singleton graph (loaded once at startup) ─────────────────────────────────
_engine = GraphEngine()


class Query(BaseModel):
    query: str


# ── /graph/full  →  full graph for initial canvas render ────────────────────
@app.get("/graph/full")
def full_graph():
    return _engine.full_graph_export()


# ── /query  →  NL query → graph or text answer ──────────────────────────────
@app.post("/query")
async def query_endpoint(q: Query):
    try:
        result = handle_query(q.query, _engine)
        # Safety: strip edges whose endpoints are not in node set
        if result.get("type") == "graph":
            node_ids = {str(n["id"]) for n in result.get("nodes", [])}
            result["edges"] = [
                e for e in result.get("edges", [])
                if str(e.get("from")) in node_ids and str(e.get("to")) in node_ids
            ]
        return {"answer": result}
    except Exception as e:
        log.error("Query error: %s", e, exc_info=True)
        return {"answer": {"type": "text", "explanation": "An internal error occurred."}}


# ── /health ──────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    G = _engine.G
    return {
        "status": "ok",
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
    }