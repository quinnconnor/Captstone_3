"""
Translates a natural language question into a SQL query against the
Redshift warehouse, using Claude via Bedrock. The generated query is
never trusted directly -- it must pass through sql_validator.validate_sql()
before execution (see query_interface.py).
"""
from ai_query_layer.bedrock_client import invoke_claude

SCHEMA_CONTEXT = """
Tables available in the Redshift warehouse:

structured_data(record_id, source_file, source_type, ingested_at, raw_payload)
document_embeddings(chunk_id, document_id, s3_key, chunk_text, embedding_vector, opensearch_doc_id, loaded_at)
customer_metrics(metric_date, total_customers, churned_customers, churn_rate, source_file)
glue_catalog_metadata(dataset_name, column_name, data_type, is_required_field, is_present, catalog_synced_at)
"""

SQL_GENERATION_PROMPT_TEMPLATE = """You write read-only SQL for a Redshift warehouse.

Schema:
{schema}

Rules:
- Only ever write a single SELECT statement.
- Never write DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, GRANT, or REVOKE.
- Never write more than one statement (no semicolon-separated stacked statements).
- Return ONLY the SQL query, no explanation, no markdown code fences.

Question: {question}

SQL query:"""


def generate_sql(question: str) -> str:
    prompt = SQL_GENERATION_PROMPT_TEMPLATE.format(schema=SCHEMA_CONTEXT, question=question)
    result = invoke_claude(prompt, max_tokens=300, call_type="sql_generation")
    sql = result["text"].strip()

    # Strip markdown fences if the model adds them despite instructions.
    if sql.startswith("```"):
        sql = sql.strip("`")
        if sql.lower().startswith("sql"):
            sql = sql[3:]
    return sql.strip()


if __name__ == "__main__":
    print(generate_sql("What is the average churn rate for Q3 2026?"))
