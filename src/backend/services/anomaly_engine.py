import pandas as pd
import os
import json

BASE_PATH = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_PATH, "../data/sap-o2c-data")

def load_jsonl(folder):
    data = []
    path = os.path.join(DATA_PATH, folder)

    for file in os.listdir(path):
        if file.endswith(".jsonl"):
            with open(os.path.join(path, file)) as f:
                for line in f:
                    data.append(json.loads(line))

    return pd.DataFrame(data)


def detect_broken_flows():
    sales = load_jsonl("sales_order_items")
    billing = load_jsonl("billing_document_items")

    billed_orders = set(billing["referenceSdDocument"].astype(str))
    all_orders = set(sales["salesOrder"].astype(str))

    missing = list(all_orders - billed_orders)[:10]

    return [{"salesOrder": m, "status": "Not Billed"} for m in missing]