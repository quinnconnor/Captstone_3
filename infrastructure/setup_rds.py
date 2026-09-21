"""
Provisions the RDS schema used to store raw extracted text (from Textract)
for structured querying and traceability back to the source S3 object.

Assumes the RDS Postgres instance itself already exists in the sandbox
(created via console or a separate boto3 rds.create_db_instance call); this
script focuses on the schema, which is what the pipeline actually depends on.
"""
import psycopg2

from config import RDS_HOST, RDS_PORT, RDS_DB_NAME, RDS_USER, RDS_PASSWORD

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id     SERIAL PRIMARY KEY,
    s3_key          TEXT NOT NULL UNIQUE,
    source_bucket   TEXT NOT NULL,
    file_type       TEXT NOT NULL,
    ingested_at     TIMESTAMP DEFAULT NOW(),
    page_count      INTEGER,
    status          TEXT DEFAULT 'processed'
);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id        SERIAL PRIMARY KEY,
    document_id     INTEGER REFERENCES documents(document_id),
    chunk_index     INTEGER NOT NULL,
    chunk_text      TEXT NOT NULL,
    token_count     INTEGER NOT NULL,
    opensearch_doc_id TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
    ON document_chunks (document_id);
"""


def get_connection():
    return psycopg2.connect(
        host=RDS_HOST, port=RDS_PORT, dbname=RDS_DB_NAME,
        user=RDS_USER, password=RDS_PASSWORD,
    )


def apply_schema():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()
        print("RDS schema applied: documents, document_chunks")
    finally:
        conn.close()


if __name__ == "__main__":
    apply_schema()
