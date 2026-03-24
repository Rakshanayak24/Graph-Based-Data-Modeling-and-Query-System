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


def run_sql(query):
    billing = load_jsonl("billing_document_items")

    result = (
        billing.groupby("material")["billingDocument"]
        .count()
        .reset_index(name="billing_count")
        .sort_values(by="billing_count", ascending=False)
        .head(5)
    )

    return result.to_dict(orient="records")