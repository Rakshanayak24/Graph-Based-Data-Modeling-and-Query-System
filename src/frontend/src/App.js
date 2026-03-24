import React, { useState, useRef, useEffect, useCallback } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";

cytoscape.use(fcose);

const API = "http://127.0.0.1:8000";

/* ─── Type colors ────────────────────────────────────────────────────────── */
const TYPE_META = {
  sales_order:      { color: "#5b9cf6", label: "Sales Order" },
  sales_order_item: { color: "#93bbfa", label: "SO Item" },
  delivery:         { color: "#f5a623", label: "Delivery" },
  billing:          { color: "#e8453c", label: "Billing" },
  journal:          { color: "#4caf50", label: "Journal Entry" },
  payment:          { color: "#26c6da", label: "Payment" },
  customer:         { color: "#ba68c8", label: "Customer" },
  product:          { color: "#ff7043", label: "Product" },
  plant:            { color: "#8d6e63", label: "Plant" },
  address:          { color: "#90a4ae", label: "Address" },
  missing:          { color: "#e53935", label: "Missing" },
  unknown:          { color: "#bdbdbd", label: "Unknown" },
};

/* ─── Themes ─────────────────────────────────────────────────────────────── */
const THEMES = {
  light: {
    bg: "#f4f7fb", surface: "#ffffff", topbar: "rgba(244,247,251,0.95)",
    border: "#dde4ee", text: "#1a1a2e", textMuted: "#999", textFaint: "#bbb",
    inputBg: "#fafbfd", chipBg: "#f4f7fb", chipBorder: "#dde4ee", chipText: "#555",
    msgBot: "#f0f4ff", msgBotText: "#1a1a2e", msgUser: "#1a1a2e", msgUserText: "#ffffff",
    btnDark: "#1a1a2e", btnDarkText: "#fff", btnLight: "rgba(255,255,255,0.9)",
    btnLightText: "#444", btnLightBorder: "#d4dce9",
    legendBg: "rgba(255,255,255,0.97)", cardBg: "#fff", cardBorder: "#e4e9f2",
    cardHeader: "#f8fafd", graphBg: "#f4f7fb",
    nodeLabel: "#333", edgeColor: "#6a9fc4",
    overlayBg: "rgba(244,247,251,0.72)",
  },
  dark: {
    bg: "#0d1117", surface: "#161b22", topbar: "rgba(13,17,23,0.95)",
    border: "#30363d", text: "#e6edf3", textMuted: "#7d8590", textFaint: "#484f58",
    inputBg: "#0d1117", chipBg: "#161b22", chipBorder: "#30363d", chipText: "#8b949e",
    msgBot: "#1c2128", msgBotText: "#e6edf3", msgUser: "#1f6feb", msgUserText: "#ffffff",
    btnDark: "#1f6feb", btnDarkText: "#fff", btnLight: "rgba(22,27,34,0.9)",
    btnLightText: "#8b949e", btnLightBorder: "#30363d",
    legendBg: "rgba(22,27,34,0.97)", cardBg: "#161b22", cardBorder: "#30363d",
    cardHeader: "#0d1117", graphBg: "#0d1117",
    nodeLabel: "#cdd9e5", edgeColor: "#4d8ab5",
    overlayBg: "rgba(13,17,23,0.72)",
  },
};

/* ─── Stylesheet factory ─────────────────────────────────────────────────── */
const makeStylesheet = (T, granular) => [
  {
    selector: "node",
    style: {
      // Tiny dots matching target screenshot
      width: granular ? 5 : 9,
      height: granular ? 5 : 9,
      label: granular ? "" : "data(shortId)",  // hidden in dot mode
      color: T.nodeLabel,
      "text-valign": "center",
      "text-halign": "center",
      "font-size": "5px",
      "font-family": "monospace",
      "border-width": 0,
      "background-color": "#5b9cf6",
      "overlay-opacity": 0,
      "transition-property": "width, height, border-width, opacity",
      "transition-duration": "200ms",
    },
  },
  ...Object.entries(TYPE_META).map(([type, { color }]) => ({
    selector: `node[type="${type}"]`,
    style: { "background-color": color },
  })),
  {
    selector: "edge",
    style: {
      // Image 2 style: ultra thin straight lines, very light, NO arrows
      width: 0.7,
      "line-color": T.edgeColor,
      "target-arrow-shape": "none",
      "curve-style": "haystack",
      opacity: 0.45,
      "overlay-opacity": 0,
    },
  },
  // Highlighted path
  { selector: ".hl-node", style: { "border-width": 2.5, "border-color": "#1a73e8", width: 18, height: 18, "z-index": 500, opacity: 1 } },
  { selector: ".hl-edge",  style: { "line-color": "#1a73e8", "target-arrow-shape": "triangle", "target-arrow-color": "#1a73e8", "arrow-scale": 1.2, width: 2.5, opacity: 1, "font-size": "9px", color: "#1a73e8", "text-background-opacity": 0.9 } },
  { selector: ".dimmed",   style: { opacity: 0.05 } },
  // Keep edges visible while dragging a node
  { selector: "node:grabbed", style: { opacity: 1, "z-index": 9999 } },
  { selector: "node:grabbed ~ edge", style: { opacity: 1 } },
  { selector: ".focused",  style: { "border-width": 3, "border-color": T.text, width: 22, height: 22, "z-index": 9999, opacity: 1 } },
];

/* ─── Legend ─────────────────────────────────────────────────────────────── */
function Legend({ theme }) {
  const T = THEMES[theme];
  const items = ["sales_order","delivery","billing","journal","payment","customer","product","plant"];
  return (
    <div style={{
      position: "absolute", bottom: 20, left: 16, zIndex: 20,
      background: T.legendBg, borderRadius: 10,
      padding: "10px 15px", fontSize: 11,
      border: `1px solid ${T.border}`,
      boxShadow: "0 2px 12px rgba(0,0,0,0.09)",
    }}>
      {items.map(type => (
        <div key={type} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ width: 9, height: 9, borderRadius: "50%", background: TYPE_META[type].color, flexShrink: 0 }} />
          <span style={{ color: T.text, fontSize: 11 }}>{TYPE_META[type].label}</span>
        </div>
      ))}
    </div>
  );
}

/* ─── Node Detail Card ───────────────────────────────────────────────────── */
function NodeCard({ node, onClose, theme }) {
  if (!node) return null;
  const T = THEMES[theme];
  const typeLabel = TYPE_META[node.type]?.label || node.type || "Entity";
  const skip  = new Set(["id", "label", "shortId", "_connections", "type"]);
  const rows  = Object.entries(node).filter(([k]) => !skip.has(k));
  const shown = rows.slice(0, 12);
  const extra = rows.length - shown.length;

  return (
    <div style={{
      position: "absolute", left: "calc(50% - 175px)", top: 52,
      width: 350, zIndex: 200,
      background: T.cardBg, borderRadius: 14,
      boxShadow: "0 8px 36px rgba(0,0,0,0.16)",
      border: `1px solid ${T.cardBorder}`,
      overflow: "hidden",
    }}>
      <div style={{ background: T.cardHeader, padding: "12px 18px 9px", borderBottom: `1px solid ${T.cardBorder}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: T.text }}>{typeLabel}</span>
        <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 20, color: T.textMuted, cursor: "pointer" }}>×</button>
      </div>
      <div style={{ padding: "10px 18px 6px", maxHeight: 420, overflowY: "auto" }}>
        <Row k="Entity" v={typeLabel} T={T} />
        {shown.map(([k, v]) => <Row key={k} k={k} v={v === true ? "true" : v === false ? "false" : (String(v) || "—")} T={T} />)}
        {extra > 0 && <p style={{ fontSize: 11, color: T.textFaint, fontStyle: "italic", margin: "4px 0" }}>Additional fields hidden for readability</p>}
        <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 8, marginTop: 6 }}>
          <Row k="Connections" v={String(node._connections ?? 0)} T={T} bold />
        </div>
      </div>
      <div style={{ height: 10 }} />
    </div>
  );
}

function Row({ k, v, T, bold }) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 4, fontSize: 12, alignItems: "flex-start" }}>
      <span style={{ minWidth: 145, flexShrink: 0, fontWeight: 600, color: T.text }}>{k}:</span>
      <span style={{ color: bold ? T.text : T.textMuted, fontWeight: bold ? 700 : 400, wordBreak: "break-all" }}>{v}</span>
    </div>
  );
}

/* ─── Bar chart for top products ─────────────────────────────────────────── */
function ProductChart({ items, theme }) {
  const T   = THEMES[theme];
  const max = Math.max(...items.map(x => x.count));
  return (
    <div style={{ marginTop: 8, width: "100%" }}>
      {items.map((item, i) => (
        <div key={i} style={{ marginBottom: 5 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: T.textMuted, marginBottom: 2 }}>
            <span style={{ fontFamily: "monospace", color: T.text }}>{item.id}</span>
            <span style={{ fontWeight: 700, color: "#ff7043" }}>{item.count} bills</span>
          </div>
          <div style={{ background: T.border, borderRadius: 3, height: 6, overflow: "hidden" }}>
            <div style={{
              width: `${(item.count / max) * 100}%`,
              height: "100%",
              background: "linear-gradient(90deg, #ff7043, #ff5722)",
              borderRadius: 3,
              transition: "width 0.8s ease",
            }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─── Chat Bubble ────────────────────────────────────────────────────────── */
function Bubble({ m, theme }) {
  const T   = THEMES[theme];
  const bot = m.role === "bot";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: bot ? "flex-start" : "flex-end", marginBottom: 14 }}>
      {bot && (
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 6 }}>
          <div style={{ width: 34, height: 34, borderRadius: "50%", background: T.btnDark, display: "flex", alignItems: "center", justifyContent: "center", color: T.btnDarkText, fontWeight: 700, fontSize: 14, flexShrink: 0 }}>D</div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: T.text }}>Dodge AI</div>
            <div style={{ fontSize: 11, color: T.textMuted }}>Graph Agent</div>
          </div>
        </div>
      )}
      <div style={{
        maxWidth: "92%", background: bot ? T.msgBot : T.msgUser, color: bot ? T.msgBotText : T.msgUserText,
        padding: "10px 14px", borderRadius: bot ? "4px 16px 16px 16px" : "16px 16px 4px 16px",
        fontSize: 13, lineHeight: 1.55, whiteSpace: "pre-line",
        boxShadow: bot ? "0 1px 4px rgba(0,0,0,0.06)" : "none",
      }}>
        {m.bold
          ? <span>Hi! I can help you analyze the <b>Order to Cash</b> process.</span>
          : m.text}
        {/* Rich bar chart for top products */}
        {m.chartItems && <ProductChart items={m.chartItems} theme={theme} />}
        {/* Trace summary table */}
        {m.traceRows && (
          <table style={{ marginTop: 8, width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <tbody>
              {m.traceRows.map((r, i) => (
                <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                  <td style={{ padding: "3px 6px", color: T.textMuted, fontFamily: "monospace" }}>{r.type}</td>
                  <td style={{ padding: "3px 6px", color: T.text, fontFamily: "monospace", fontWeight: 600 }}>{r.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {!bot && <div style={{ width: 26, height: 26, borderRadius: "50%", background: T.border, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, color: T.textMuted, marginTop: 4 }}>You</div>}
    </div>
  );
}

/* ─── App ────────────────────────────────────────────────────────────────── */
export default function App() {
  const [theme, setTheme]               = useState("light");
  const [allElems, setAllElems]         = useState([]);
  const [elements, setElements]         = useState([]);
  const [messages, setMessages]         = useState([{ role: "bot", text: "", bold: true }]);
  const [query, setQuery]               = useState("");
  const [loading, setLoading]           = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [graphStatus, setGraphStatus]   = useState("Loading graph…");
  const [minimized, setMinimized]       = useState(false);
  const [granular, setGranular]         = useState(true);   // true = tiny dots (overlay mode)
  const [chips, setChips]               = useState([
    "top products", "broken flows",
    "trace billing 90504204", "show customer 310000108",
  ]);

  const cyRef  = useRef(null);
  const endRef = useRef(null);
  const T = THEMES[theme];

  /* ── Load full graph ──────────────────────────────────────────────────── */
  useEffect(() => {
    fetch(`${API}/graph/full`)
      .then(r => r.json())
      .then(({ nodes = [], edges = [] }) => {
        // Derive real chip IDs from actual data
        const byType = (t) => nodes.filter(n => n.type === t).map(n => n.id);
        const bilIds  = byType("billing");
        const soIds   = byType("sales_order");
        const cuIds   = byType("customer");
        const jIds    = byType("journal");

        setChips([
          "top products",
          "broken flows",
          ...(bilIds[0]  ? [`trace billing ${bilIds[0]}`]   : []),
          ...(bilIds[1]  ? [`trace billing ${bilIds[1]}`]   : []),
          ...(soIds[0]   ? [`trace order ${soIds[0]}`]      : []),
          ...(cuIds[0]   ? [`show customer ${cuIds[0]}`]    : []),
          ...(cuIds[1]   ? [`show customer ${cuIds[1]}`]    : []),
          ...(jIds[0]    ? [`${jIds[0]} find journal entry`]: []),
        ].slice(0, 8));

        const nodeSet = new Set(nodes.map(n => String(n.id)));
        const cyNodes = nodes.map(n => ({
          data: { ...n, id: String(n.id), label: String(n.id), shortId: tail(String(n.id), 7), type: n.type || "unknown" },
        }));
        const cyEdges = edges
          .filter(e => nodeSet.has(String(e.from)) && nodeSet.has(String(e.to)))
          .map((e, i) => ({ data: { id: `e${i}`, source: String(e.from), target: String(e.to), label: e.label || "" } }));

        const all = [...cyNodes, ...cyEdges];
        setAllElems(all);
        setElements(all);
        setGraphStatus(`${cyNodes.length} nodes · ${cyEdges.length} edges`);
      })
      .catch(() => setGraphStatus("⚠️ Backend not reachable — run: uvicorn main:app --reload"));
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  /* ── Re-apply stylesheet when granular/theme toggles ─────────────────── */
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.style(makeStylesheet(T, granular));
  }, [granular, theme]);

  /* ── Focus node ──────────────────────────────────────────────────────── */
  const focusNode = useCallback((cy, nodeId) => {
    const t = cy.getElementById(String(nodeId));
    if (!t.length) return;
    cy.elements().addClass("dimmed").removeClass("hl-node hl-edge focused");
    t.removeClass("dimmed").addClass("focused hl-node");
    t.connectedEdges().removeClass("dimmed").addClass("hl-edge");
    t.neighborhood().nodes().removeClass("dimmed").addClass("hl-node");
    cy.animate({ center: { eles: t }, zoom: Math.min(cy.zoom() * 2, 4) }, { duration: 700, easing: "ease-in-out-cubic" });
  }, []);

  /* ── Run query ───────────────────────────────────────────────────────── */
  const runQuery = async () => {
    const q = query.trim();
    if (!q || loading) return;
    setMessages(p => [...p, { role: "user", text: q }]);
    setQuery("");
    setLoading(true);
    setSelectedNode(null);
    if (minimized) setMinimized(false);

    try {
      const res  = await fetch(`${API}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      const data = await res.json();
      const ans  = data.answer;
      // Build rich message payload
      const msgPayload = { role: "bot", text: ans.explanation || "Done." };
      // Top products → attach bar chart data
      if (ans.nodes?.length && ans.nodes[0]?.type === "product" && ans.nodes[0]?.billingCount) {
        msgPayload.chartItems = ans.nodes
          .filter(n => n.billingCount)
          .sort((a, b) => b.billingCount - a.billingCount)
          .slice(0, 15)
          .map(n => ({ id: String(n.id).slice(-10), count: Number(n.billingCount) }));
      }
      // Trace → attach summary rows showing the chain
      if (ans.highlight && ans.nodes?.length) {
        const typeOrder = { customer: 0, sales_order: 1, delivery: 2, billing: 3, journal: 4, payment: 5 };
        const chainNodes = ans.nodes
          .filter(n => typeOrder[n.type] !== undefined)
          .sort((a, b) => (typeOrder[a.type] ?? 9) - (typeOrder[b.type] ?? 9))
          .slice(0, 8);
        if (chainNodes.length > 1) {
          msgPayload.traceRows = chainNodes.map(n => ({
            type: (TYPE_META[n.type]?.label || n.type).padEnd(12),
            id: String(n.id),
          }));
        }
      }
      setMessages(p => [...p, msgPayload]);

      if (ans.type === "graph" && ans.nodes?.length) {
        const nodeSet = new Set(ans.nodes.map(n => String(n.id)));
        const cyNodes = ans.nodes.map(n => ({
          data: { ...n, id: String(n.id), label: String(n.id), shortId: tail(String(n.id), 7), type: n.type || "unknown" },
        }));
        const cyEdges = (ans.edges || [])
          .filter(e => nodeSet.has(String(e.from)) && nodeSet.has(String(e.to)))
          .map((e, i) => ({ data: { id: `q${i}`, source: String(e.from), target: String(e.to), label: e.label || "" } }));
        setElements([...cyNodes, ...cyEdges]);
        setTimeout(() => {
          const cy = cyRef.current;
          if (!cy) return;
          cy.layout(buildLayout(cyNodes.length, cyEdges.length)).run();
          if (ans.highlight) setTimeout(() => focusNode(cy, ans.highlight), 1000);
        }, 200);
      }
    } catch {
      setMessages(p => [...p, { role: "bot", text: "⚠️ Could not reach backend." }]);
    } finally {
      setLoading(false);
    }
  };

  /* ── Reset ───────────────────────────────────────────────────────────── */
  const resetGraph = () => {
    setElements(allElems);
    setSelectedNode(null);
    setMinimized(false);
    setTimeout(() => {
      const cy = cyRef.current;
      if (!cy) return;
      cy.elements().removeClass("hl-node hl-edge dimmed focused");
      cy.layout(buildLayout(allElems.filter(e => !e.data.source).length, allElems.filter(e => e.data.source).length)).run();
    }, 100);
  };

  /* ── Node/bg tap ─────────────────────────────────────────────────────── */
  const onNodeTap = useCallback(evt => {
    const cy   = cyRef.current;
    const node = evt.target;
    cy.elements().removeClass("hl-node hl-edge focused").addClass("dimmed");
    node.removeClass("dimmed").addClass("focused");
    node.connectedEdges().removeClass("dimmed").addClass("hl-edge");
    node.neighborhood().nodes().removeClass("dimmed");
    setSelectedNode({ ...node.data(), _connections: node.connectedEdges().length });
  }, []);

  const onBgTap = useCallback(evt => {
    if (evt.target === cyRef.current) {
      cyRef.current?.elements().removeClass("hl-node hl-edge dimmed focused");
      setSelectedNode(null);
    }
  }, []);

  return (
    <div style={{ display: "flex", width: "100vw", height: "100vh", background: T.bg, overflow: "hidden", fontFamily: "'Segoe UI', system-ui, sans-serif" }}>

      {/* ═══ GRAPH ═══════════════════════════════════════════════════════ */}
      <div style={{
        flex: minimized ? "0 0 0px" : "1",
        minWidth: 0,
        position: "relative",
        overflow: "hidden",
        transition: "flex 0.3s ease",
        opacity: minimized ? 0 : 1,
      }}>
        {/* Top bar */}
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, height: 44, zIndex: 30,
          background: T.topbar, backdropFilter: "blur(8px)",
          borderBottom: `1px solid ${T.border}`,
          display: "flex", alignItems: "center", padding: "0 14px", gap: 8,
        }}>
          <span style={{ fontSize: 17, color: T.textMuted, cursor: "pointer" }}>☰</span>
          <span style={{ color: T.textMuted, fontSize: 13 }}>Mapping</span>
          <span style={{ color: T.textFaint }}>/</span>
          <span style={{ color: T.text, fontWeight: 700, fontSize: 14 }}>Order to Cash</span>
          <span style={{ color: T.textMuted, fontSize: 11, marginLeft: 6 }}>{graphStatus}</span>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
            <TBtn T={T} onClick={() => setMinimized(p => !p)}>
              {minimized ? "⤡ Expand" : "⤢ Minimize"}
            </TBtn>
            {/* WORKING granular toggle — changes node size & label visibility */}
            <TBtn T={T} onClick={() => setGranular(p => !p)}>
              {granular ? "⊞ Hide Granular Overlay" : "⊟ Show Granular Overlay"}
            </TBtn>
            <TBtn T={T} onClick={resetGraph} accent>↺ Reset Graph</TBtn>
          </div>
        </div>

        {/* Canvas */}
        {elements.length > 0 && !minimized && (
          <CytoscapeComponent
            key={`cy-${theme}`}
            elements={elements}
            style={{ width: "100%", height: "100%", paddingTop: 44, background: T.graphBg }}
            layout={buildLayout(elements.filter(e => !e.data.source).length, elements.filter(e => e.data.source).length)}
            stylesheet={makeStylesheet(T, granular)}
            cy={cy => {
              cyRef.current = cy;
              cy.removeAllListeners();
              cy.on("tap", "node", onNodeTap);
              cy.on("tap", onBgTap);
            }}
          />
        )}

        {elements.length === 0 && (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: T.textMuted, fontSize: 13, paddingTop: 44 }}>
            {graphStatus}
          </div>
        )}

        {!minimized && <Legend theme={theme} />}
        {!minimized && selectedNode && (
          <NodeCard node={selectedNode} theme={theme} onClose={() => {
            setSelectedNode(null);
            cyRef.current?.elements().removeClass("hl-node hl-edge dimmed focused");
          }} />
        )}
      </div>

      {/* Minimized tab */}
      {minimized && (
        <div onClick={() => setMinimized(false)} style={{
          width: 28, flexShrink: 0, background: T.surface,
          borderRight: `1px solid ${T.border}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          cursor: "pointer", writingMode: "vertical-rl",
          fontSize: 11, color: T.textMuted, letterSpacing: 1, userSelect: "none",
        }}>▶ Graph</div>
      )}

      {/* ═══ CHAT PANEL ══════════════════════════════════════════════════ */}
      <div style={{
        width: 380, flexShrink: 0, background: T.surface,
        borderLeft: `1px solid ${T.border}`,
        display: "flex", flexDirection: "column",
        boxShadow: "-2px 0 16px rgba(0,0,0,0.05)",
      }}>
        {/* Header + theme toggle */}
        <div style={{ padding: "13px 18px 10px", borderBottom: `1px solid ${T.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: T.text }}>Chat with Graph</div>
            <div style={{ fontSize: 11, color: T.textMuted, marginTop: 1 }}>Order to Cash</div>
          </div>
          <button onClick={() => setTheme(p => p === "light" ? "dark" : "light")} style={{
            background: T.chipBg, border: `1px solid ${T.border}`,
            borderRadius: 8, padding: "5px 10px",
            fontSize: 16, cursor: "pointer", color: T.text, lineHeight: 1,
          }}>
            {theme === "light" ? "🌙" : "☀️"}
          </button>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "14px 18px" }}>
          {messages.map((m, i) => <Bubble key={i} m={m} theme={theme} />)}
          {loading && <div style={{ color: T.textFaint, fontSize: 12, paddingLeft: 44 }}><span style={{ animation: "blink 1.2s infinite" }}>● ● ●</span></div>}
          <div ref={endRef} />
        </div>

        {/* Status + chips */}
        <div style={{ padding: "10px 18px 0", borderTop: `1px solid ${T.border}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#4caf50", display: "inline-block" }} />
            <span style={{ fontSize: 11, color: T.textMuted }}>Dodge AI is awaiting instructions</span>
          </div>
          <div style={{ fontSize: 11, color: T.textFaint, marginBottom: 8 }}>Analyze anything</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
            {chips.map(c => (
              <button key={c} onClick={() => setQuery(c)} style={{
                background: T.chipBg, border: `1px solid ${T.chipBorder}`,
                borderRadius: 20, padding: "4px 11px", fontSize: 11,
                color: T.chipText, cursor: "pointer",
                transition: "opacity 0.15s",
              }}
              onMouseEnter={e => e.currentTarget.style.opacity = "0.7"}
              onMouseLeave={e => e.currentTarget.style.opacity = "1"}
              >{c}</button>
            ))}
          </div>
        </div>

        {/* Input */}
        <div style={{ padding: "8px 18px 16px", display: "flex", gap: 8 }}>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && runQuery()}
            placeholder="Analyze anything"
            style={{
              flex: 1, padding: "9px 13px",
              border: `1px solid ${T.border}`, borderRadius: 9,
              fontSize: 13, outline: "none",
              background: T.inputBg, color: T.text,
              transition: "border-color 0.15s",
            }}
            onFocus={e => e.target.style.borderColor = "#5b9cf6"}
            onBlur={e => e.target.style.borderColor = T.border}
          />
          <button onClick={runQuery} disabled={loading} style={{
            padding: "9px 16px", borderRadius: 9, border: "none",
            background: loading ? T.textFaint : T.btnDark,
            color: T.btnDarkText, fontWeight: 700, fontSize: 13,
            cursor: loading ? "not-allowed" : "pointer",
          }}>{loading ? "…" : "Send"}</button>
        </div>
      </div>

      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: ${T.border}; border-radius: 3px; }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.15} }
      `}</style>
    </div>
  );
}

/* ─── Helpers ────────────────────────────────────────────────────────────── */
const tail = (s, n) => s.length <= n ? s : s.slice(-n);

function TBtn({ children, onClick, accent, T }) {
  return (
    <button onClick={onClick} style={{
      background: accent ? T.btnDark : T.btnLight,
      border: `1px solid ${accent ? T.btnDark : T.btnLightBorder}`,
      borderRadius: 7, padding: "4px 12px", fontSize: 11,
      color: accent ? T.btnDarkText : T.btnLightText,
      cursor: "pointer", backdropFilter: "blur(4px)",
    }}>{children}</button>
  );
}

function buildLayout(n, edgeCount = 0) {
  // ── No edges at all (e.g. top products) → neat grid with correct node size ──
  if (edgeCount === 0 && n <= 20) {
    return {
      name: "grid",
      animate: true,
      animationDuration: 500,
      fit: true,
      padding: 60,
      avoidOverlap: true,
      avoidOverlapPadding: 20,
      condense: false,
      rows: Math.ceil(Math.sqrt(n)),
    };
  }

  // ── Small result (<25 nodes) ─────────────────────────────────────────────
  if (n < 25) {
    return {
      name: "fcose",
      animate: true, animationDuration: 600, animationEasing: "ease-out-cubic",
      quality: "proof", randomize: false, fit: true, padding: 80,
      nodeRepulsion: 22000, idealEdgeLength: 150, edgeElasticity: 0.1,
      nestingFactor: 0.01, gravity: 0.04, gravityRange: 1.0, numIter: 3000, tile: false,
    };
  }

  // ── Medium (25–300 nodes) ────────────────────────────────────────────────
  if (n <= 300) {
    return {
      name: "fcose",
      animate: true,
      animationDuration: 1000,
      animationEasing: "ease-out-cubic",
      quality: "default",
      randomize: true,
      fit: true,
      padding: 60,
      nodeRepulsion: 8000,
      idealEdgeLength: 100,
      edgeElasticity: 0.2,
      nestingFactor: 0.1,
      gravity: 0.15,
      gravityRange: 2.5,
      numIter: 3000,
      tile: false,
    };
  }

  // ── Full graph (>300 nodes) — tuned to produce Image 2 cluster style ────
  return {
    name: "fcose",
    animate: true,
    animationDuration: 2000,
    animationEasing: "ease-out-cubic",
    quality: "draft",
    randomize: true,
    fit: true,
    padding: 30,
    // Moderate repulsion + strong edge pull → hub clusters form naturally
    nodeRepulsion: 4500,
    idealEdgeLength: 50,
    edgeElasticity: 0.45,
    nestingFactor: 0.1,
    gravity: 0.25,
    gravityRange: 2.8,
    numIter: 2500,
    tile: false,
  };
}