"""
Given a natural language question, decides whether it needs:
  - "opensearch"  (semantic/document search over unstructured PDFs)
  - "redshift"    (SQL/structured data)
  - "both"        (synthesis: needs structured data AND documented policy/context)

Uses Claude via Bedrock for classification, with a strict single-word
output contract so the result is trivial to parse.
"""
import re

from ai_query_layer.bedrock_client import invoke_claude

ROUTING_PROMPT_TEMPLATE = """You are a query router for a data platform with two backends:

- OPENSEARCH: semantic search over unstructured document text (policies, strategy docs, governance docs, PDFs).
- REDSHIFT: SQL queries over structured data (customer metrics, churn rates, Glue catalog metadata, counts, aggregates).

Classify the question below into exactly one label: OPENSEARCH, REDSHIFT, or BOTH.
Use BOTH only when the question requires combining a documented policy/strategy (OPENSEARCH)
with a structured/numeric fact (REDSHIFT) into a single synthesized answer.

Question: {question}

Respond with exactly one word: OPENSEARCH, REDSHIFT, or BOTH."""


def route_query(question: str) -> str:
    prompt = ROUTING_PROMPT_TEMPLATE.format(question=question)
    result = invoke_claude(prompt, max_tokens=10, call_type="classification")
    label = re.sub(r"[^A-Z]", "", result["text"].upper())

    if "BOTH" in label:
        return "both"
    if "OPENSEARCH" in label:
        return "opensearch"
    if "REDSHIFT" in label:
        return "redshift"

    # Fail-safe default: if the model returns something unexpected, prefer
    # the broader "both" path so we don't silently drop relevant context.
    return "both"


if __name__ == "__main__":
    examples = [
        "What does our retention strategy document recommend for at-risk customers?",
        "What is the average churn rate for Q3 2026?",
        "Does our current customer churn rate align with what our documented retention strategy says we should be seeing?",
    ]
    for q in examples:
        print(f"{route_query(q):10s} <- {q}")
