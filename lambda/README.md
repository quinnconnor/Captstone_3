# Lambda Deployment Notes

## `pdf_ingest_lambda.py`

This function loads a Sentence Transformers model (`torch` + `sentence-transformers`),
which is too large for a standard zip-based Lambda deployment package.

**Recommended deployment: container image.**

1. Build a Docker image using the `public.ecr.aws/lambda/python:3.12` base image,
   installing `requirements.txt` plus the project's `embeddings/`, `infrastructure/`,
   and `config.py` modules.
2. Push to ECR.
3. Create the Lambda function from the container image.
4. Set memory to **>= 1024 MB** and timeout to **>= 60s** (model load on cold start
   plus Textract call time).
5. Attach the `CapstoneLambdaIngestionRole` IAM role (see `infrastructure/setup_iam.py`).
6. Set environment variables matching `.env.example` (or pull from Secrets Manager,
   which the IAM policy already grants access to).
7. If RDS/OpenSearch are in a VPC, attach this Lambda to the same VPC/subnets/security
   groups, with a NAT gateway or VPC endpoints for S3/Textract/Bedrock access.

## `structured_data_trigger_lambda.py`

Lightweight — only calls `boto3` Glue APIs, no heavy dependencies. Standard zip
deployment is fine. Set timeout to ~30s and attach the same `CapstoneLambdaIngestionRole`
(it only needs the Glue-related permissions from that role, or split into a
dedicated minimal role if you prefer stricter separation).

## Wiring S3 -> Lambda

After both functions are deployed, run:

```python
from infrastructure import setup_s3
setup_s3.add_lambda_permission("pdf-ingest-function-name")
setup_s3.add_lambda_permission("structured-data-trigger-function-name")
setup_s3.configure_event_notifications(pdf_lambda_arn, structured_lambda_arn)
```
