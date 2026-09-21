"""
Runs 10 representative queries end-to-end through the AI query layer
(mixing standard OpenSearch, standard Redshift, and both required harder
synthesis queries), logging token usage for every Bedrock call along the
way, then prints the required cost summary.

Run with: python tests/run_10_query_tokenomics_test.py
"""
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_query_layer.query_interface import answer_question
from ai_query_layer.tokenomics import print_cost_summary, cost_summary, reset_call_log

TEST_QUERIES = [
    "What is the average churn rate for Q3 2026?",
    "How many customers churned in the last recorded month?",
    "What does our documented retention strategy recommend for at-risk customers?",
    "What onboarding steps does our customer success playbook describe?",
    "List all datasets currently catalogued by Glue.",
    "What is the total customer count across all recorded months?",
    "What does our data governance policy say about required metadata fields?",
    "Does our current customer churn rate (from the data warehouse) align with what "
    "our documented retention strategy says we should be seeing?",
    "Based on our data governance policy documents, are any of the currently-ingested "
    "datasets missing required metadata fields (check against the Glue Catalog)?",
    "What is the churn rate trend compared to what our retention strategy targets?",
]


def main():
    reset_call_log()
    results = []

    for i, question in enumerate(TEST_QUERIES, start=1):
        print(f"\n[{i}/10] {question}")
        try:
            result = answer_question(question)
            print(f"  route={result['route']}")
            results.append({"question": question, "route": result["route"], "ok": True})
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"question": question, "error": str(e), "ok": False})

    print_cost_summary()

    summary = cost_summary()
    with open("tokenomics_summary.json", "w") as f:
        json.dump({"query_results": results, "cost_summary": summary}, f, indent=2, default=str)
    print("\nWrote tokenomics_summary.json")


if __name__ == "__main__":
    main()
