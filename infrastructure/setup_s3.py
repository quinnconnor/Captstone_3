"""
Creates (or verifies) the central S3 bucket and wires up event notifications
so that any object uploaded under raw/ triggers the ingestion Lambda.
"""
import json
import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION, S3_BUCKET_NAME, AWS_ACCOUNT_ID

s3 = boto3.client("s3", region_name=AWS_REGION)
lambda_client = boto3.client("lambda", region_name=AWS_REGION)


def create_bucket():
    try:
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=S3_BUCKET_NAME)
        else:
            s3.create_bucket(
                Bucket=S3_BUCKET_NAME,
                CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
            )
        print(f"Created bucket: {S3_BUCKET_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"Bucket already exists: {S3_BUCKET_NAME}")
        else:
            raise

    # Enable versioning for auditability of raw document uploads.
    s3.put_bucket_versioning(
        Bucket=S3_BUCKET_NAME, VersioningConfiguration={"Status": "Enabled"}
    )

    # Standard prefix layout.
    for prefix in ("raw/pdf/", "raw/csv/", "raw/json/", "processed/", "charts/"):
        s3.put_object(Bucket=S3_BUCKET_NAME, Key=prefix)
    print("Initialized folder structure: raw/pdf, raw/csv, raw/json, processed, charts")


def add_lambda_permission(lambda_function_name: str):
    """Allow S3 to invoke the given Lambda function."""
    try:
        lambda_client.add_permission(
            FunctionName=lambda_function_name,
            StatementId="AllowS3Invoke",
            Action="lambda:InvokeFunction",
            Principal="s3.amazonaws.com",
            SourceArn=f"arn:aws:s3:::{S3_BUCKET_NAME}",
            SourceAccount=AWS_ACCOUNT_ID,
        )
        print(f"Granted S3 invoke permission to {lambda_function_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            print("Permission already granted.")
        else:
            raise


def configure_event_notifications(pdf_lambda_arn: str, structured_lambda_arn: str):
    """
    Routes raw/pdf/* uploads to the PDF ingestion Lambda, and
    raw/csv/*, raw/json/* uploads to the structured-data ingestion Lambda.
    """
    notification_config = {
        "LambdaFunctionConfigurations": [
            {
                "LambdaFunctionArn": pdf_lambda_arn,
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {"FilterRules": [{"Name": "prefix", "Value": "raw/pdf/"}]}
                },
            },
            {
                "LambdaFunctionArn": structured_lambda_arn,
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {"FilterRules": [{"Name": "prefix", "Value": "raw/csv/"}]}
                },
            },
            {
                "LambdaFunctionArn": structured_lambda_arn,
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {"FilterRules": [{"Name": "prefix", "Value": "raw/json/"}]}
                },
            },
        ]
    }
    s3.put_bucket_notification_configuration(
        Bucket=S3_BUCKET_NAME, NotificationConfiguration=notification_config
    )
    print("S3 event notifications configured for PDF and structured-data prefixes.")


if __name__ == "__main__":
    create_bucket()
    print("Run add_lambda_permission() and configure_event_notifications() "
          "after Lambda functions are deployed (see scripts/deploy_all.py).")
