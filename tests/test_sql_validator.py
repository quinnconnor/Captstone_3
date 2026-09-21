"""
Test suite for the SQL validation layer. Run with: pytest tests/test_sql_validator.py -v

Includes the required minimum of 5 cases, plus a dedicated stacked-query
injection attempt, before this validator is ever wired into a live
Redshift connection.
"""
import pytest

from ai_query_layer.sql_validator import validate_sql


def test_valid_select_passes():
    result = validate_sql("SELECT * FROM customer_metrics WHERE churn_rate > 0.1")
    assert result["valid"] is True


def test_valid_lowercase_select_passes():
    result = validate_sql("select dataset_name from glue_catalog_metadata where is_present = false")
    assert result["valid"] is True


def test_stacked_query_drop_is_blocked():
    """The specific stacked-query attack pattern called out in the assignment."""
    result = validate_sql("SELECT * FROM customer_metrics; DROP TABLE customer_metrics;")
    assert result["valid"] is False
    assert "DROP" in result["reason"]


def test_delete_is_blocked():
    result = validate_sql("DELETE FROM structured_data WHERE record_id = 1")
    assert result["valid"] is False


def test_update_is_blocked():
    result = validate_sql("UPDATE customer_metrics SET churn_rate = 0")
    assert result["valid"] is False


def test_insert_is_blocked():
    result = validate_sql("INSERT INTO customer_metrics VALUES (CURRENT_DATE, 100, 5, 0.05, 'x')")
    assert result["valid"] is False


def test_non_select_statement_is_blocked():
    result = validate_sql("GRANT ALL ON customer_metrics TO PUBLIC")
    assert result["valid"] is False


def test_two_stacked_selects_is_blocked():
    """Even a benign-looking second statement should be blocked -- only ONE
    statement is ever permitted."""
    result = validate_sql(
        "SELECT * FROM structured_data WHERE source_file = 'a'; SELECT * FROM customer_metrics;"
    )
    assert result["valid"] is False


def test_drop_table_alone_is_blocked():
    result = validate_sql("DROP TABLE structured_data")
    assert result["valid"] is False
    assert "DROP" in result["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
