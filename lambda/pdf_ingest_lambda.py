"""
Lambda handler triggered on S3 upload under raw/pdf/.

Flow:
  1. Download the PDF from S3 (or call Textract directly against the S3 object).
  2. Extract text via Amazon Textract.
  3. Chunk the text into 500-1000 token windows (embeddings.chunker).
  4. Generate an embedding per chunk using Sentence Transformers (local --
     Bedrock embedding models are denied in this sandbox, see embedder.py).
  5. Store raw text + chunk metadata in RDS.
  6. Store the embedding vectors in OpenSearch for semantic search.

Deploy note: Sentence Transformers + torch are large dependencies. Package
this Lambda with a container image (not a zip) or attach a Lambda Layer
built for the target architecture, and give the function enough memory
(>= 1024 MB) and a timeout of at least 60s to load the model on cold start.
"""
import json
import os
import sys
import uuid

import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AWS_REGION, OPENSEARCH_INDEX, CHUNK_MIN_TOKENS, CHUNK_MAX_TOKENS
from embeddings.chunker import chunk_text
from embeddings.embedder import embed_batch
from infrastructure.setup_rds import get_connection as get_rds_connection
from infrastructure.setup_opensearch import get_client as get_opensearch_client

textract = boto3.client("textract", region_name=AWS_REGION)


def extract_text_with_textract(bucket: str, key: str) -> str:
    response = textract.detect_document_text(
        Document={"S3Object": {"Bucket": bucket, "Name": key}}
    )
    lines = [
        block["Text"] for block in response.get("Blocks", [])
        if block["BlockType"] == "LINE"
    ]
    return "\n".join(lines)


def store_in_rds(bucket: str, key: str, chunks_with_embeddings: list) -> int:
    conn = get_rds_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (s3_key, source_bucket, file_type, status)
                VALUES (%s, %s, 'pdf', 'processed')
                ON CONFLICT (s3_key) DO UPDATE SET status = 'processed'
                RETURNING document_id
                """,
                (key, bucket),
            )
            document_id = cur.fetchone()[0]

            for chunk in chunks_with_embeddings:
                cur.execute(
                    """
                    INSERT INTO document_chunks
                        (document_id, chunk_index, chunk_text, token_count, opensearch_doc_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        document_id, chunk["chunk_index"], chunk["text"],
                        chunk["token_count"], chunk["opensearch_doc_id"],
                    ),
                )
        conn.commit()
        return document_id
    finally:
        conn.close()


def store_in_opensearch(document_id: int, bucket_key: str, chunks_with_embeddings: list):
    client = get_opensearch_client()
    for chunk in chunks_with_embeddings:
        client.index(
            index=OPENSEARCH_INDEX,
            id=chunk["opensearch_doc_id"],
            body={
                "document_id": document_id,
                "s3_key": bucket_key,
                "chunk_index": chunk["chunk_index"],
                "chunk_text": chunk["text"],
                "embedding": chunk["embedding"],
            },
        )


def lambda_handler(event, context):
    results = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        print(f"Processing s3://{bucket}/{key}")

        raw_text = extract_text_with_textract(bucket, key)
        chunks = chunk_text(raw_text, min_tokens=CHUNK_MIN_TOKENS, max_tokens=CHUNK_MAX_TOKENS)

        embeddings = embed_batch([c["text"] for c in chunks])
        for chunk, vector in zip(chunks, embeddings):
            chunk["embedding"] = vector
            chunk["opensearch_doc_id"] = str(uuid.uuid4())

        document_id = store_in_rds(bucket, key, chunks)
        store_in_opensearch(document_id, key, chunks)

        results.append({
            "s3_key": key, "document_id": document_id, "chunks_created": len(chunks),
        })
        print(f"Stored {len(chunks)} chunks for document_id={document_id}")

    return {"statusCode": 200, "body": json.dumps(results)}
