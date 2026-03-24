import os
import glob
import json
import pandas as pd
import networkx as nx

# ── DATA_PATH: works locally AND in Railway/Render deployment ───────────────
# For deployment: copy your data folder to src/backend/data/sap-o2c-data/
# Or set DATA_PATH environment variable to override
DATA_PATH = os.environ.get(
    "DATA_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sap-o2c-data")
)
# Local Windows fallback (used when running locally before deployment)
if not os.path.exists(DATA_PATH):
    _win = r"C:\Users\Raksha\Downloads\fde_dodge_ai_001\src\backend\data\sap-o2c-data"
    if os.path.exists(_win):
        DATA_PATH = _win


class GraphEngine:
    def __init__(self):
        print("🔥  Initialising GraphEngine…")
        self.G = nx.DiGraph()
        self._load_all()
        self._build()
        print(f"✅  Graph ready: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges")

    # ──────────────────────────── I/O ───────────────────────────────────────
    def _jsonl(self, folder: str) -> pd.DataFrame:
        rows = []
        for f in glob.glob(os.path.join(DATA_PATH, folder, "*.jsonl")):
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except Exception:
                            pass
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def _load_all(self):
        self.df_so_hdr   = self._jsonl("sales_order_headers")
        self.df_so_item  = self._jsonl("sales_order_items")
        self.df_so_sched = self._jsonl("sales_order_schedule_lines")
        self.df_del_hdr  = self._jsonl("outbound_delivery_headers")
        self.df_del_item = self._jsonl("outbound_delivery_items")
        self.df_bil_can  = self._jsonl("billing_document_cancellations")
        self.df_bil_hdr  = self._jsonl("billing_document_headers")
        self.df_bil_item = self._jsonl("billing_document_items")
        self.df_journal  = self._jsonl("journal_entry_items_accounts_receivable")
        self.df_payment  = self._jsonl("payments_accounts_receivable")
        self.df_bp       = self._jsonl("business_partners")
        self.df_bp_addr  = self._jsonl("business_partner_addresses")
        self.df_cust_co  = self._jsonl("customer_company_assignments")
        self.df_cust_sa  = self._jsonl("customer_sales_area_assignments")
        self.df_products = self._jsonl("products")
        self.df_prod_d   = self._jsonl("product_descriptions")
        self.df_prod_p   = self._jsonl("product_plants")
        self.df_prod_s   = self._jsonl("product_storage_locations")
        self.df_plants   = self._jsonl("plants")

        # Build a fast customer-name lookup  {bp_id: full_name}
        self._cust_name: dict[str, str] = {}
        if not self.df_bp.empty and "businessPartner" in self.df_bp.columns:
            for _, r in self.df_bp.iterrows():
                bp  = str(r.get("businessPartner", ""))
                nm  = str(r.get("businessPartnerFullName", "") or r.get("businessPartnerName", ""))
                if bp:
                    self._cust_name[bp] = nm

    # ──────────────────────────── GRAPH ────────────────────────────────────
    def _node(self, nid, ntype, **kw):
        nid = str(nid)
        if not self.G.has_node(nid):
            self.G.add_node(nid, type=ntype, **kw)
        else:
            self.G.nodes[nid].update(kw)
        return nid

    def _edge(self, src, tgt, rel):
        s, t = str(src), str(tgt)
        if s and t and s != "nan" and t != "nan" and s != t:
            self.G.add_edge(s, t, relation=rel)

    def _build(self):
        # ── Customers ─────────────────────────────────────────────────────
        for _, r in self.df_bp.iterrows():
            self._node(r.get("businessPartner"), "customer",
                       name=r.get("businessPartnerFullName", ""),
                       grouping=r.get("businessPartnerGrouping", ""),
                       blocked=str(r.get("businessPartnerIsBlocked", "")),
                       archived=str(r.get("isMarkedForArchiving", "")),
                       creationDate=str(r.get("creationDate", "")),
                       lastChangeDate=str(r.get("lastChangeDate", "")))

        for _, r in self.df_bp_addr.iterrows():
            aid = self._node(r.get("addressId"), "address",
                             city=r.get("cityName", ""),
                             country=r.get("country", ""),
                             postalCode=str(r.get("postalCode", "")),
                             street=r.get("streetName", ""),
                             region=r.get("region", ""),
                             timezone=r.get("addressTimeZone", ""))
            self._edge(r.get("businessPartner"), aid, "has_address")

        # ── Products ──────────────────────────────────────────────────────
        prod_desc = {}
        for _, r in self.df_prod_d.iterrows():
            prod_desc[str(r.get("product", ""))] = r.get("productDescription", "")

        for _, r in self.df_products.iterrows():
            pid = str(r.get("product", ""))
            self._node(pid, "product",
                       description=prod_desc.get(pid, ""),
                       productType=r.get("productType", ""),
                       productGroup=r.get("productGroup", ""),
                       grossWeight=str(r.get("grossWeight", "")),
                       weightUnit=r.get("weightUnit", ""),
                       baseUnit=r.get("baseUnit", ""),
                       division=r.get("division", ""),
                       productOldId=r.get("productOldId", ""))

        # ── Plants ────────────────────────────────────────────────────────
        for _, r in self.df_plants.iterrows():
            self._node(r.get("plant"), "plant",
                       plantName=r.get("plantName", ""),
                       salesOrg=r.get("salesOrganization", ""),
                       distributionChannel=r.get("distributionChannel", ""))

        for _, r in self.df_prod_p.iterrows():
            self._edge(r.get("product"), r.get("plant"), "stored_at_plant")

        # ── Sales Orders ──────────────────────────────────────────────────
        for _, r in self.df_so_hdr.iterrows():
            so = self._node(r.get("salesOrder"), "sales_order",
                            totalNetAmount=str(r.get("totalNetAmount", "")),
                            currency=r.get("transactionCurrency", ""),
                            soldToParty=str(r.get("soldToParty", "")),
                            creationDate=str(r.get("creationDate", "")),
                            deliveryStatus=r.get("overallDeliveryStatus", ""),
                            billingStatus=r.get("overallOrdReltdBillgStatus", ""),
                            salesOrg=r.get("salesOrganization", ""),
                            salesOrderType=r.get("salesOrderType", ""),
                            paymentTerms=r.get("customerPaymentTerms", ""),
                            requestedDeliveryDate=str(r.get("requestedDeliveryDate", "")))
            cust = str(r.get("soldToParty", ""))
            if cust and cust != "nan":
                self._edge(cust, so, "placed_order")

        for _, r in self.df_so_item.iterrows():
            so   = str(r.get("salesOrder", ""))
            item = f"SOI_{so}_{r.get('salesOrderItem', '')}"
            self._node(item, "sales_order_item",
                       salesOrder=so,
                       salesOrderItem=str(r.get("salesOrderItem", "")),
                       material=str(r.get("material", "")),
                       requestedQuantity=str(r.get("requestedQuantity", "")),
                       requestedQuantityUnit=str(r.get("requestedQuantityUnit", "")),
                       netAmount=str(r.get("netAmount", "")),
                       currency=r.get("transactionCurrency", ""),
                       materialGroup=r.get("materialGroup", ""),
                       productionPlant=r.get("productionPlant", ""))
            self._edge(so, item, "has_item")
            mat = str(r.get("material", ""))
            if mat and mat != "nan":
                self._edge(item, mat, "references_product")

        # ── Deliveries ────────────────────────────────────────────────────
        for _, r in self.df_del_hdr.iterrows():
            self._node(r.get("deliveryDocument"), "delivery",
                       shippingPoint=r.get("shippingPoint", ""),
                       creationDate=str(r.get("creationDate", "")),
                       pickingStatus=r.get("overallPickingStatus", ""),
                       goodsMovementStatus=r.get("overallGoodsMovementStatus", ""),
                       deliveryBlockReason=r.get("deliveryBlockReason", ""),
                       headerBillingBlockReason=r.get("headerBillingBlockReason", ""))

        for _, r in self.df_del_item.iterrows():
            d   = str(r.get("deliveryDocument", ""))
            so  = str(r.get("referenceSdDocument", ""))
            pnt = str(r.get("plant", ""))
            self._edge(so, d, "delivered_via")
            if pnt and pnt != "nan":
                self._edge(d, pnt, "ships_from_plant")

        # ── Billing ───────────────────────────────────────────────────────
        cancelled_bills = set()
        if not self.df_bil_can.empty and "billingDocument" in self.df_bil_can.columns:
            cancelled_bills = set(self.df_bil_can["billingDocument"].astype(str))

        for _, r in self.df_bil_hdr.iterrows():
            bid = str(r.get("billingDocument", ""))
            self._node(bid, "billing",
                       billingDocumentType=r.get("billingDocumentType", ""),
                       totalNetAmount=str(r.get("totalNetAmount", "")),
                       currency=r.get("transactionCurrency", ""),
                       isCancelled=str(bid in cancelled_bills),
                       companyCode=r.get("companyCode", ""),
                       fiscalYear=str(r.get("fiscalYear", "")),
                       accountingDocument=str(r.get("accountingDocument", "")),
                       billingDate=str(r.get("billingDocumentDate", "")),
                       soldToParty=str(r.get("soldToParty", "")))

        for _, r in self.df_bil_item.iterrows():
            b   = str(r.get("billingDocument", ""))
            ref = str(r.get("referenceSdDocument", ""))
            if ref and ref != "nan":
                self._edge(ref, b, "billed_via")
            mat = str(r.get("material", ""))
            if mat and mat != "nan":
                self._edge(b, mat, "billed_product")

        # ── Journal Entries ───────────────────────────────────────────────
        for _, r in self.df_journal.iterrows():
            j = self._node(r.get("accountingDocument"), "journal",
                           companyCode=r.get("companyCode", ""),
                           fiscalYear=str(r.get("fiscalYear", "")),
                           accountingDocument=str(r.get("accountingDocument", "")),
                           glAccount=str(r.get("glAccount", "")),
                           referenceDocument=str(r.get("referenceDocument", "")),
                           profitCenter=r.get("profitCenter", ""),
                           transactionCurrency=r.get("transactionCurrency", ""),
                           amountInTransactionCurrency=str(r.get("amountInTransactionCurrency", "")),
                           companyCodeCurrency=r.get("companyCodeCurrency", ""),
                           amountInCompanyCodeCurrency=str(r.get("amountInCompanyCodeCurrency", "")),
                           postingDate=str(r.get("postingDate", "")),
                           documentDate=str(r.get("documentDate", "")),
                           accountingDocumentType=r.get("accountingDocumentType", ""),
                           accountingDocumentItem=str(r.get("accountingDocumentItem", "")),
                           customer=str(r.get("customer", "")),
                           financialAccountType=r.get("financialAccountType", ""),
                           clearingDate=str(r.get("clearingDate", "")),
                           clearingAccountingDocument=str(r.get("clearingAccountingDocument", "")))
            ref = str(r.get("referenceDocument", ""))
            if ref and ref != "nan":
                self._edge(ref, j, "journal_entry")

        # ── Payments ──────────────────────────────────────────────────────
        for _, r in self.df_payment.iterrows():
            p = self._node(r.get("accountingDocument"), "payment",
                           companyCode=r.get("companyCode", ""),
                           fiscalYear=str(r.get("fiscalYear", "")),
                           amountInTransactionCurrency=str(r.get("amountInTransactionCurrency", "")),
                           transactionCurrency=r.get("transactionCurrency", ""),
                           amountInCompanyCodeCurrency=str(r.get("amountInCompanyCodeCurrency", "")),
                           companyCodeCurrency=r.get("companyCodeCurrency", ""),
                           postingDate=str(r.get("postingDate", "")),
                           documentDate=str(r.get("documentDate", "")),
                           customer=str(r.get("customer", "")),
                           clearingDate=str(r.get("clearingDate", "")),
                           clearingAccountingDocument=str(r.get("clearingAccountingDocument", "")))
            clr = str(r.get("clearingAccountingDocument", ""))
            if clr and clr != "nan":
                self._edge(clr, p, "cleared_by_payment")

    # ─────────────────────────── PUBLIC API ─────────────────────────────────
    def trace(self, start_id: str) -> dict:
        sid = str(start_id)
        if sid not in self.G:
            return {"type": "text",
                    "explanation": f"Entity '{sid}' not found in the graph. Try a billing document, sales order, or journal number."}

        visited, nodes, edges = set(), [], []
        queue = [sid]
        while queue:
            cur = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            attrs = dict(self.G.nodes[cur])
            nodes.append({"id": cur, "label": cur, **attrs})
            for nxt in self.G.successors(cur):
                edges.append({"from": cur, "to": nxt, "label": self.G[cur][nxt].get("relation", "")})
                queue.append(nxt)
            for prv in self.G.predecessors(cur):
                edges.append({"from": prv, "to": cur, "label": self.G[prv][cur].get("relation", "")})
                queue.append(prv)

        return {
            "type": "graph",
            "nodes": nodes[:250],
            "edges": edges[:500],
            "highlight": sid,
            "explanation": f"Full O2C trace for entity {sid}",
        }

    def get_top_products(self) -> dict:
        count: dict[str, int] = {}
        for _, r in self.df_bil_item.iterrows():
            m = str(r.get("material", ""))
            if m and m != "nan":
                count[m] = count.get(m, 0) + 1

        top = sorted(count.items(), key=lambda x: x[1], reverse=True)[:15]
        nodes = []
        for pid, c in top:
            attrs = dict(self.G.nodes[pid]) if self.G.has_node(pid) else {}
            nodes.append({"id": pid, "label": pid, "type": "product",
                          "billingCount": c, **attrs})
        return {
            "type": "graph",
            "nodes": nodes,
            "edges": [],
            "explanation": f"Top {len(top)} products by billing document count.",
        }

    def get_broken_flows(self) -> dict:
        seen:  set   = set()
        nodes: list  = []
        edges: list  = []
        missing_nodes: list = []
        broken = 0

        def _add(nid, ntype):
            if nid not in seen:
                seen.add(nid)
                attrs = dict(self.G.nodes[nid]) if self.G.has_node(nid) else {}
                nodes.append({"id": nid, "label": nid, "type": ntype, **attrs})

        so_ids = (self.df_so_hdr["salesOrder"].dropna().astype(str).unique()
                  if not self.df_so_hdr.empty else [])

        for so in so_ids:
            if so not in self.G:
                continue
            deliveries = [n for n in self.G.successors(so)
                          if self.G.nodes[n].get("type") == "delivery"]
            if not deliveries:
                _add(so, "sales_order")
                mid = f"MISSING_DEL_{so}"
                missing_nodes.append({"id": mid, "label": "⚠ No Delivery", "type": "missing"})
                edges.append({"from": so, "to": mid, "label": "MISSING"})
                broken += 1
                continue
            for d in deliveries:
                _add(so, "sales_order"); _add(d, "delivery")
                edges.append({"from": so, "to": d, "label": "delivered_via"})
                billings = [n for n in self.G.successors(d)
                            if self.G.nodes[n].get("type") == "billing"]
                if not billings:
                    mid = f"MISSING_BIL_{d}"
                    missing_nodes.append({"id": mid, "label": "⚠ No Billing", "type": "missing"})
                    edges.append({"from": d, "to": mid, "label": "MISSING"})
                    broken += 1

        all_nodes = (nodes + missing_nodes)[:300]
        return {
            "type": "graph",
            "nodes": all_nodes,
            "edges": edges[:500],
            "explanation": f"{broken} broken/incomplete O2C flows detected.",
        }

    def get_customer_info(self, cust_id: str) -> dict:
        cid = str(cust_id)
        if cid not in self.G:
            return {"type": "text", "explanation": f"Customer {cid} not found."}
        attrs = dict(self.G.nodes[cid])
        name  = self._cust_name.get(cid, attrs.get("name", cid))

        neighbors = list(self.G.successors(cid))[:30]
        nodes = [{"id": cid, "label": cid, "type": "customer", **attrs}]
        for n in neighbors:
            na = dict(self.G.nodes[n])
            nodes.append({"id": n, "label": n, "type": na.get("type", "unknown"), **na})
        edges = [{"from": cid, "to": n, "label": self.G[cid][n].get("relation", "")} for n in neighbors]

        return {
            "type": "graph",
            "nodes": nodes,
            "edges": edges,
            "highlight": cid,
            "explanation": f"Customer {cid}: {name}",
        }

    def lookup_journal_for_billing(self, billing_id: str) -> dict:
        """
        Find journal entry linked to billing_id.
        Returns a FULL trace: Customer → SO → Delivery → Billing → Journal → Payment
        with the journal node highlighted.
        """
        bid = str(billing_id)

        # 1. Walk graph successors (fast path)
        journal_ids = [n for n in self.G.successors(bid)
                       if self.G.nodes[n].get("type") == "journal"]

        # 2. Fallback: scan DataFrame by referenceDocument
        if not journal_ids and not self.df_journal.empty:
            if "referenceDocument" in self.df_journal.columns:
                matches = self.df_journal[
                    self.df_journal["referenceDocument"].astype(str) == bid
                ]
                journal_ids = matches["accountingDocument"].astype(str).tolist()

        # 3. Maybe user passed accountingDocument instead of billingDocument
        if not journal_ids and not self.df_bil_hdr.empty:
            if "accountingDocument" in self.df_bil_hdr.columns:
                row = self.df_bil_hdr[
                    self.df_bil_hdr["accountingDocument"].astype(str) == bid
                ]
                if not row.empty:
                    real_bid = str(row.iloc[0]["billingDocument"])
                    return self.lookup_journal_for_billing(real_bid)

        if not journal_ids:
            return {
                "type": "text",
                "explanation": (
                    f"No journal entry found linked to billing document {bid}. "
                    f"Tip: use the billingDocument number (e.g. 90504248), "
                    f"not the accountingDocument number."
                ),
            }

        j     = journal_ids[0]
        nodes: list = []
        edges: list = []
        seen:  set  = set()

        def _add(nid, ntype=None):
            nid = str(nid)
            if nid in seen:
                return
            seen.add(nid)
            a = dict(self.G.nodes[nid]) if self.G.has_node(nid) else {}
            t = ntype or a.get("type", "unknown")
            nodes.append({"id": nid, "label": nid, "type": t, **a})

        # Forward: billing → journal → payment
        _add(bid, "billing")
        _add(j,   "journal")
        edges.append({"from": bid, "to": j, "label": "journal_entry"})

        for nxt in (self.G.successors(j) if self.G.has_node(j) else []):
            if self.G.nodes[nxt].get("type") == "payment":
                _add(nxt, "payment")
                edges.append({"from": j, "to": nxt, "label": "cleared_by_payment"})

        # Backward: delivery → billing → and SO → delivery
        for prv in list(self.G.predecessors(bid) if self.G.has_node(bid) else []):
            ptype = self.G.nodes[prv].get("type")
            if ptype == "delivery":
                _add(prv, "delivery")
                edges.append({"from": prv, "to": bid, "label": "billed_via"})
                for so in self.G.predecessors(prv):
                    if self.G.nodes[so].get("type") == "sales_order":
                        _add(so, "sales_order")
                        edges.append({"from": so, "to": prv, "label": "delivered_via"})
                        for cu in self.G.predecessors(so):
                            if self.G.nodes[cu].get("type") == "customer":
                                _add(cu, "customer")
                                edges.append({"from": cu, "to": so, "label": "placed_order"})
            elif ptype == "sales_order":
                _add(prv, "sales_order")
                edges.append({"from": prv, "to": bid, "label": "billed_via"})

        return {
            "type": "graph",
            "nodes": nodes,
            "edges": edges,
            "highlight": j,
            "explanation": (
                f"The journal entry number linked to billing document {bid} is {j}."
            ),
        }

    def full_graph_export(self) -> dict:
        nodes = []
        for nid, attrs in self.G.nodes(data=True):
            nodes.append({"id": str(nid), **attrs})
        edges = []
        for s, t, d in self.G.edges(data=True):
            edges.append({"from": str(s), "to": str(t), "label": d.get("relation", "")})
        return {"nodes": nodes, "edges": edges}