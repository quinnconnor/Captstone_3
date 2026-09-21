"""
Orchestrates full pipeline setup in the order recommended by the
assignment: infrastructure first, AI layer second, each verified before
moving to the next stage.

This script assumes Lambda deployment packages/container images have
already been built and pushed (packaging Sentence Transformers + torch
for Lambda is environment-specific -- see lambda/README.md) and focuses on
wiring together the AWS resources via boto3.

Run with: python scripts/deploy_all.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure import setup_s3, setup_rds, setup_opensearch, setup_redshift, setup_iam
from glue import setup_glue_crawler


def main():
    print("=== Step 1: IAM roles ===")
    lambda_role_arn = setup_iam.create_lambda_ingestion_role()
    glue_role_arn = setup_iam.create_glue_role()
    setup_iam.create_redshift_copy_role()

    print("\n=== Step 2: S3 bucket + folder structure ===")
    setup_s3.create_bucket()

    print("\n=== Step 3: RDS schema ===")
    setup_rds.apply_schema()

    print("\n=== Step 4: OpenSearch index ===")
    setup_opensearch.create_index()

    print("\n=== Step 5: Redshift schema ===")
    setup_redshift.apply_schema()

    print("\n=== Step 6: Glue database + crawler ===")
    setup_glue_crawler.create_database_if_missing()
    setup_glue_crawler.create_crawler(glue_role_arn)

    print("\n=== Infrastructure setup complete ===")
    print("Next steps:")
    print("  1. Deploy lambda/pdf_ingest_lambda.py and "
          "lambda/structured_data_trigger_lambda.py (see lambda/README.md).")
    print("  2. Run: python infrastructure/setup_s3.py -> "
          "configure_event_notifications() with the deployed Lambda ARNs.")
    print("  3. Run: python scripts/test_bedrock_connection.py to confirm Bedrock access.")
    print("  4. Upload test documents to raw/pdf/, raw/csv/, raw/json/ and verify data flow.")
    print("  5. Run: pytest tests/ -v")
    print("  6. Run: python tests/run_10_query_tokenomics_test.py")
    print("  7. Run: python visualization/generate_charts.py")


if __name__ == "__main__":
    main()
