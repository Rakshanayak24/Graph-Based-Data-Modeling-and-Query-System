# services/llm_engine.py

from groq import Groq
import os

client = Groq(api_key=os.getenv("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"))

def generate_query_plan(user_query):
    prompt = f"""
You are a system that converts user queries into structured actions.

Return JSON:
{{
 "intent": "trace | aggregation | anomaly",
 "target": "billing | sales | product",
 "filters": {{}}
}}

Query: {user_query}
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content
