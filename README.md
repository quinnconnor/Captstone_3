# Intelligent Document Search & AI Query Capstone (AWS)

An end-to-end pipeline that ingests unstructured PDFs and structured CSV/JSON
files, makes them searchable and SQL-queryable, and exposes a natural-language
AI query layer (via Claude on Bedrock) that can route questions across a
vector store and a data warehouse — including synthesis queries that combine
both into a single, cited answer.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full data flow
diagram and service-by-service breakdown.

## Two Implementation Notes (read before deploying)

1. **Embeddings use Sentence Transformers, not Bedrock.** Both Bedrock
   embedding model families (`amazon.titan-embed-text-v2:0`,
   `cohere.embed-english-v3`) are denied in this sandbox — confirmed by direct
   testing, and a structural permissions gap rather than a model-specific one.
   `embeddings/embedder.py` runs `all-MiniLM-L6-v2` locally instead. Claude
   (text generation) via Bedrock is confirmed working and is used throughout.
2. **All Bedrock/Claude calls use the inference-profile ARN**, not the bare
   model ID — newer Claude models on Bedrock require this, or you'll hit a
   `ValidationException`. See `ai_query_layer/bedrock_client.py` and
   `config.BEDROCK_MODEL_ARN`.

## Repository Structure

```
.
├── config.py                          # Central env/config loader
├── requirements.txt
├── .env.example                       # Copy to .env and fill in
├── infrastructure/
│   ├── setup_s3.py                    # Bucket + event notifications
│   ├── setup_rds.py                   # Raw text schema
│   ├── setup_opensearch.py            # k-NN vector index
│   ├── setup_redshift.py              # Warehouse schema
│   └── setup_iam.py                   # Least-privilege roles
├── lambda/
│   ├── pdf_ingest_lambda.py           # Textract -> chunk -> embed -> RDS/OpenSearch
│   ├── structured_data_trigger_lambda.py  # Kicks off Glue crawler + ETL
│   └── README.md                      # Packaging notes (container image needed)
├── glue/
│   ├── setup_glue_crawler.py
│   └── etl_normalize_load_job.py      # PySpark Glue ETL job
├── embeddings/
│   ├── chunker.py                     # 500-1000 token chunking
│   └── embedder.py                    # Sentence Transformers (local)
├── ai_query_layer/
│   ├── bedrock_client.py              # invoke_claude() w/ inference-profile ARN
│   ├── router.py                      # OpenSearch / Redshift / both classification
│   ├── sql_generator.py               # NL -> SQL
│   ├── sql_validator.py               # Required validation layer
│   ├── redshift_executor.py           # Only executes validated SQL
│   ├── rag_responder.py               # Retrieval + grounded, cited generation
│   ├── synthesis.py                   # Combines both sources into one answer
│   ├── query_interface.py             # Top-level entry point
│   └── tokenomics.py                  # Token/cost logging + summary
├── visualization/
│   └── generate_charts.py             # 2+ matplotlib charts from Redshift
├── scripts/
│   ├── test_bedrock_connection.py     # Standalone smoke test (run first!)
│   └── deploy_all.py                  # Orchestrates infra setup
├── tests/
│   ├── test_sql_validator.py          # 9 cases incl. stacked-query attempt
│   ├── test_query_layer.py            # Routing + both harder synthesis queries
│   └── run_10_query_tokenomics_test.py
└── docs/
    └── ARCHITECTURE.md                # Diagram + implementation notes
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Fill in your sandbox's AWS account ID, region, and resource
   # hostnames/credentials (RDS, OpenSearch, Redshift).
   ```

3. **Confirm Bedrock access before building anything else**
   ```bash
   python scripts/test_bedrock_connection.py
   ```
   This must return a real response using the inference-profile ARN before
   proceeding — if it fails, don't debug the AI query layer, debug this call.

4. **Provision infrastructure**
   ```bash
   python scripts/deploy_all.py
   ```
   This creates IAM roles, the S3 bucket, RDS schema, OpenSearch index,
   Redshift schema, and the Glue database/crawler, in that order.

5. **Deploy Lambda functions** — see [`lambda/README.md`](lambda/README.md).
   `pdf_ingest_lambda.py` needs a container-image deployment because of the
   `sentence-transformers`/`torch` dependency size.

6. **Wire S3 event notifications to the deployed Lambdas**
   ```python
   from infrastructure import setup_s3
   setup_s3.add_lambda_permission("<pdf-lambda-name>")
   setup_s3.add_lambda_permission("<structured-lambda-name>")
   setup_s3.configure_event_notifications(pdf_lambda_arn, structured_lambda_arn)
   ```

7. **Test end-to-end ingestion** — upload a PDF to `raw/pdf/` and a CSV/JSON
   to `raw/csv/` or `raw/json/`, then confirm rows appear in RDS, OpenSearch,
   and Redshift.

8. **Run the validator test suite**
   ```bash
   pytest tests/test_sql_validator.py -v
   ```

9. **Run the AI query layer tests** (requires populated data)
   ```bash
   pytest tests/test_query_layer.py -v -s
   ```

10. **Run the 10-query tokenomics test**
    ```bash
    python tests/run_10_query_tokenomics_test.py
    ```

11. **Generate BI charts**
    ```bash
    python visualization/generate_charts.py
    ```

## Must-Have Checklist (Bronze) — Where Each Item Lives

| Requirement | Implementation |
|---|---|
| S3 stores raw PDFs, CSVs, JSONs | `infrastructure/setup_s3.py` |
| Lambda triggers on upload; calls Textract for PDFs | `lambda/pdf_ingest_lambda.py` |
| Textract extracts and chunks PDF text | `lambda/pdf_ingest_lambda.py` + `embeddings/chunker.py` |
| Sentence Transformers generates embeddings (Bedrock denied) | `embeddings/embedder.py` |
| Raw text in RDS; embeddings in OpenSearch | `infrastructure/setup_rds.py`, `infrastructure/setup_opensearch.py` |
| Glue Crawler catalogs schemas | `glue/setup_glue_crawler.py` |
| Glue ETL normalizes/validates/loads into Redshift | `glue/etl_normalize_load_job.py` |
| Redshift consolidates structured + vector data | `infrastructure/setup_redshift.py` |
| 2+ matplotlib charts | `visualization/generate_charts.py` |
| Lambda + boto3 automation | `lambda/`, `infrastructure/`, `scripts/deploy_all.py` |
| IAM least-privilege | `infrastructure/setup_iam.py` |
| AI query layer: routing, NL-to-SQL, contextual response, inference-profile ARN | `ai_query_layer/router.py`, `sql_generator.py`, `rag_responder.py`, `bedrock_client.py` |
| SQL validation layer, 5+ tests incl. stacked-query | `ai_query_layer/sql_validator.py`, `tests/test_sql_validator.py` |
| Tokenomics logging + 10-query cost summary | `ai_query_layer/tokenomics.py`, `tests/run_10_query_tokenomics_test.py` |
| Both harder synthesis queries, citing both sources | `ai_query_layer/synthesis.py`, `tests/test_query_layer.py` |

## Stretch Goals

- 🥈 **Silver — LangGraph routing refactor**: `router.py`'s single
  classification prompt is the natural place to swap in a LangGraph state
  machine (route -> generate -> validate -> execute/retrieve -> synthesize
  as explicit graph nodes) if pursuing this.
- 🥇 **Gold — Enterprise Knowledge API**: `ai_query_layer/query_interface.py`
  already exposes a single `answer_question(question)` function with no CLI
  dependencies, so it can be wrapped directly in an API Gateway + Lambda
  handler (`event["body"]["question"] -> answer_question(...) -> JSON
  response`) for programmatic access.

## Test Results

_Fill in after running against your sandbox:_

- `pytest tests/test_sql_validator.py -v` → **9/9 passed**
- `pytest tests/test_query_layer.py -v -s` → results + full answer text for
  both harder synthesis queries
- `tests/run_10_query_tokenomics_test.py` → see generated
  `tokenomics_summary.json` for per-call-type token counts and total cost
