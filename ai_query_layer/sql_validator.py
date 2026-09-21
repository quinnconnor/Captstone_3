"""
Required SQL validation layer.

No Bedrock-generated SQL query may execute against Redshift without
passing through validate_sql() first. This is deliberately simple and
conservative: SELECT-only, with a blocked-keyword scan that also catches
stacked-query injection attempts (e.g. "SELECT ...; DROP TABLE ...;").
"""

BLOCKED_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]


def validate_sql(query: str) -> dict:
    query_upper = query.upper().strip()

    for keyword in BLOCKED_KEYWORDS:
        if f" {keyword} " in f" {query_upper} " or query_upper.startswith(keyword):
            return {"valid": False, "reason": f"Blocked: {keyword} not permitted"}

    if not query_upper.startswith("SELECT"):
        return {"valid": False, "reason": "Only SELECT queries are permitted"}

    # Extra guard against stacked queries: a semicolon followed by anything
    # other than trailing whitespace means a second statement is present.
    stripped = query.strip().rstrip(";")
    if ";" in stripped:
        return {"valid": False, "reason": "Blocked: multiple/stacked statements not permitted"}

    return {"valid": True, "reason": "OK"}


def run_validation_test_suite():
    """
    Minimum 5 test cases, including at least one stacked-query attempt,
    run before wiring the validator into a live Redshift connection.
    """
    test_cases = [
        ("SELECT * FROM customer_metrics WHERE churn_rate > 0.1;", True),
        ("SELECT churn_rate FROM customer_metrics; DROP TABLE customer_metrics;", False),
        ("DELETE FROM structured_data WHERE record_id = 1", False),
        ("UPDATE customer_metrics SET churn_rate = 0", False),
        ("select dataset_name, column_name from glue_catalog_metadata where is_present = false", True),
        ("DROP TABLE structured_data", False),
        ("SELECT * FROM structured_data WHERE source_file = 'a'; SELECT * FROM customer_metrics;", False),
        ("GRANT ALL ON customer_metrics TO PUBLIC", False),
        ("SELECT COUNT(*) FROM document_embeddings", True),
        ("INSERT INTO customer_metrics VALUES (CURRENT_DATE, 100, 5, 0.05, 'x')", False),
    ]

    print("=== SQL Validator Test Suite ===")
    passed = 0
    for query, expected_valid in test_cases:
        result = validate_sql(query)
        ok = result["valid"] == expected_valid
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] expected_valid={expected_valid} got={result['valid']} "
              f"reason='{result['reason']}' | query={query[:70]}")

    print(f"\n{passed}/{len(test_cases)} test cases passed.")
    return passed == len(test_cases)


if __name__ == "__main__":
    run_validation_test_suite()
