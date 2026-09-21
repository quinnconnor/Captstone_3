"""
Central configuration loader.

Every other module in this project pulls its AWS resource names, hosts, and
credentials from here rather than hardcoding them, so the pipeline can move
between sandbox/dev/prod by only changing the .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = None, required: bool = False) -> str:
    val = os.getenv(name, default)
    if required and not val:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            f"Copy .env.example to .env and fill it in."
        )
    return val


# --- AWS core ---
AWS_REGION = _get("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = _get("AWS_ACCOUNT_ID", required=True)

# --- S3 ---
S3_BUCKET_NAME = _get("S3_BUCKET_NAME", required=True)

# --- RDS ---
RDS_HOST = _get("RDS_HOST")
RDS_PORT = int(_get("RDS_PORT", "5432"))
RDS_DB_NAME = _get("RDS_DB_NAME", "capstone_docs")
RDS_USER = _get("RDS_USER")
RDS_PASSWORD = _get("RDS_PASSWORD")

# --- OpenSearch ---
OPENSEARCH_HOST = _get("OPENSEARCH_HOST")
OPENSEARCH_PORT = int(_get("OPENSEARCH_PORT", "443"))
OPENSEARCH_INDEX = _get("OPENSEARCH_INDEX", "document-embeddings")
OPENSEARCH_USER = _get("OPENSEARCH_USER")
OPENSEARCH_PASSWORD = _get("OPENSEARCH_PASSWORD")

# --- Redshift ---
REDSHIFT_HOST = _get("REDSHIFT_HOST")
REDSHIFT_PORT = int(_get("REDSHIFT_PORT", "5439"))
REDSHIFT_DB_NAME = _get("REDSHIFT_DB_NAME", "capstone_warehouse")
REDSHIFT_USER = _get("REDSHIFT_USER")
REDSHIFT_PASSWORD = _get("REDSHIFT_PASSWORD")
REDSHIFT_IAM_ROLE_ARN = _get("REDSHIFT_IAM_ROLE_ARN")

# --- Glue ---
GLUE_DATABASE_NAME = _get("GLUE_DATABASE_NAME", "capstone_catalog")
GLUE_CRAWLER_NAME = _get("GLUE_CRAWLER_NAME", "capstone-structured-data-crawler")
GLUE_ETL_JOB_NAME = _get("GLUE_ETL_JOB_NAME", "capstone-etl-normalize-load")

# --- Bedrock / Claude ---
# Sandbox-confirmed: bare model IDs (e.g. "anthropic.claude-sonnet-4-6-v1:0")
# raise a ValidationException for newer Claude models on Bedrock. The
# inference-profile ARN is required. We build it here so every caller gets
# the correct ID automatically.
BEDROCK_MODEL_SHORT_NAME = _get("BEDROCK_MODEL_SHORT_NAME", "us.anthropic.claude-sonnet-4-6")
BEDROCK_MODEL_ARN = (
    f"arn:aws:bedrock:{AWS_REGION}:{AWS_ACCOUNT_ID}:"
    f"inference-profile/{BEDROCK_MODEL_SHORT_NAME}"
)

# --- Embeddings ---
# Sandbox-confirmed: both amazon.titan-embed-text-v2:0 and
# cohere.embed-english-v3 are denied for this account (a structural
# embeddings-capability gap, not a model-specific issue). Sentence
# Transformers runs locally, needs no API key, and is used for all
# document embeddings instead.
SENTENCE_TRANSFORMER_MODEL = _get("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")

# --- Chunking ---
CHUNK_MIN_TOKENS = int(_get("CHUNK_MIN_TOKENS", "500"))
CHUNK_MAX_TOKENS = int(_get("CHUNK_MAX_TOKENS", "1000"))
