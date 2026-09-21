"""
End-to-end tests for the AI query layer, including:
  - Standard routing to OpenSearch-only and Redshift-only queries.
  - Both new harder synthesis queries required this year, verifying the
    answer draws on and cites BOTH Redshift and OpenSearch, combined into
    a single answer.

These tests hit live AWS resources (Bedrock, OpenSearch, Redshift), so
they're meant to be run against a populated sandbox environment, not
mocked unit tests. Run with: pytest tests/test_query_layer.py -v -s
"""
import pytest

from ai_query_layer.router import route_query
from ai_query_layer.query_interface import answer_question

STANDARD_QUERIES = [
    ("What is the average churn rate for Q3 2026?", "redshift"),
    ("What does our documented retention strategy recommend for at-risk customers?", "opensearch"),
]

HARDER_SYNTHESIS_QUERIES = [
    "Does our current customer churn rate (from the data warehouse) align with what "
    "our documented retention strategy says we should be seeing?",
    "Based on our data governance policy documents, are any of the currently-ingested "
    "datasets missing required metadata fields (check against the Glue Catalog)?",
]


@pytest.mark.parametrize("question,expected_route", STANDARD_QUERIES)
def test_standard_query_routing(question, expected_route):
    route = route_query(question)
    assert route == expected_route, f"Expected {expected_route}, got {route} for: {question}"


@pytest.mark.parametrize("question", HARDER_SYNTHESIS_QUERIES)
def test_harder_synthesis_query_routes_to_both(question):
    route = route_query(question)
    assert route == "both", f"Expected 'both' routing, got '{route}' for: {question}"


@pytest.mark.parametrize("question", HARDER_SYNTHESIS_QUERIES)
def test_harder_synthesis_query_cites_both_sources(question):
    result = answer_question(question)
    assert result["route"] == "both"
    assert "sql_used" in result and result["sql_used"], "Missing Redshift SQL component"
    source_labels = str(result["sources"])
    assert "Redshift" in source_labels, "Answer does not cite Redshift"
    assert any(
        isinstance(s, dict) and "s3_key" in s for s in result["sources"]
    ), "Answer does not cite an OpenSearch/document source"
    print(f"\nQ: {question}\nA: {result['answer']}\nSources: {result['sources']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
