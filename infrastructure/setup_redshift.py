"""
Provisions the Redshift schema that acts as the unified warehouse for
structured data (loaded via Glue ETL) and vector embeddings (mirrored from
OpenSearch/RDS so they're SQL-joinable with structured tables).
"""
import redshift_connector

from config import (
    REDSHIFT_HOST, REDSHIFT_PORT, REDSHIFT_DB_NAME,
    REDSHIFT_USER, REDSHIFT_PASSWORD,
)

SCHEMA_SQL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS structured_data (
        record_id       BIGINT IDENTITY(1,1),
        source_file     VARCHAR(512),
        source_type     VARCHAR(20),
        ingested_at     TIMESTAMP DEFAULT GETDATE(),
        raw_payload     SUPER
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS document_embeddings (
        chunk_id            BIGINT,
        document_id         BIGINT,
        s3_key              VARCHAR(1024),
        chunk_text          VARCHAR(65535),
        embedding_vector    SUPER,
        opensearch_doc_id   VARCHAR(256),
        loaded_at           TIMESTAMP DEFAULT GETDATE()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS customer_metrics (
        metric_date         DATE,
        total_customers     INTEGER,
        churned_customers   INTEGER,
        churn_rate          DECIMAL(6,4),
        source_file         VARCHAR(512)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS glue_catalog_metadata (
        dataset_name        VARCHAR(256),
        column_name         VARCHAR(256),
        data_type           VARCHAR(64),
        is_required_field   BOOLEAN,
        is_present           BOOLEAN,
        catalog_synced_at   TIMESTAMP DEFAULT GETDATE()
    );
    """,
]


def get_connection():
    return redshift_connector.connect(
        host=REDSHIFT_HOST, port=REDSHIFT_PORT, database=REDSHIFT_DB_NAME,
        user=REDSHIFT_USER, password=REDSHIFT_PASSWORD,
    )


def apply_schema():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for stmt in SCHEMA_SQL_STATEMENTS:
            cursor.execute(stmt)
        conn.commit()
        print("Redshift schema applied: structured_data, document_embeddings, "
              "customer_metrics, glue_catalog_metadata")
    finally:
        conn.close()


if __name__ == "__main__":
    apply_schema()
