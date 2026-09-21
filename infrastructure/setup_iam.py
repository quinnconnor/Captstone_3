"""
Creates the IAM roles/policies the pipeline needs, following least-privilege
practice: each role only gets the permissions its own component needs
(Lambda ingestion role, Glue role, Redshift COPY role), rather than one
broad admin role shared across everything.
"""
import json
import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION, AWS_ACCOUNT_ID, S3_BUCKET_NAME

iam = boto3.client("iam", region_name=AWS_REGION)

LAMBDA_TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }],
}

GLUE_TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "glue.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }],
}

REDSHIFT_TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "redshift.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }],
}


def _create_role_if_missing(role_name: str, trust_policy: dict) -> str:
    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Capstone pipeline role: {role_name}",
        )
        print(f"Created role {role_name}")
        return resp["Role"]["Arn"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            print(f"Role {role_name} already exists")
            return iam.get_role(RoleName=role_name)["Role"]["Arn"]
        raise


def create_lambda_ingestion_role():
    role_arn = _create_role_if_missing("CapstoneLambdaIngestionRole", LAMBDA_TRUST_POLICY)

    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ReadRawWriteProcessed",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject"],
                "Resource": f"arn:aws:s3:::{S3_BUCKET_NAME}/*",
            },
            {
                "Sid": "TextractExtraction",
                "Effect": "Allow",
                "Action": ["textract:DetectDocumentText", "textract:AnalyzeDocument"],
                "Resource": "*",
            },
            {
                "Sid": "BedrockClaudeInvoke",
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel"],
                "Resource": (
                    f"arn:aws:bedrock:{AWS_REGION}:{AWS_ACCOUNT_ID}:"
                    f"inference-profile/*"
                ),
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
                ],
                "Resource": "arn:aws:logs:*:*:*",
            },
            {
                "Sid": "RDSAndOpenSearchAccessViaSecretsOrVPC",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": f"arn:aws:secretsmanager:{AWS_REGION}:{AWS_ACCOUNT_ID}:secret:capstone/*",
            },
        ],
    }
    iam.put_role_policy(
        RoleName="CapstoneLambdaIngestionRole",
        PolicyName="CapstoneLambdaIngestionPolicy",
        PolicyDocument=json.dumps(policy_doc),
    )
    print("Attached least-privilege policy to CapstoneLambdaIngestionRole")
    return role_arn


def create_glue_role():
    role_arn = _create_role_if_missing("CapstoneGlueRole", GLUE_TRUST_POLICY)
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3Access",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                "Resource": [
                    f"arn:aws:s3:::{S3_BUCKET_NAME}",
                    f"arn:aws:s3:::{S3_BUCKET_NAME}/*",
                ],
            },
            {
                "Sid": "GlueCatalogAccess",
                "Effect": "Allow",
                "Action": ["glue:*"],
                "Resource": "*",
            },
            {
                "Sid": "RedshiftDataApi",
                "Effect": "Allow",
                "Action": ["redshift-data:ExecuteStatement", "redshift:GetClusterCredentials"],
                "Resource": "*",
            },
        ],
    }
    iam.put_role_policy(
        RoleName="CapstoneGlueRole",
        PolicyName="CapstoneGluePolicy",
        PolicyDocument=json.dumps(policy_doc),
    )
    print("Attached least-privilege policy to CapstoneGlueRole")
    return role_arn


def create_redshift_copy_role():
    role_arn = _create_role_if_missing("CapstoneRedshiftCopyRole", REDSHIFT_TRUST_POLICY)
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "S3ReadForCopy",
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": [
                f"arn:aws:s3:::{S3_BUCKET_NAME}",
                f"arn:aws:s3:::{S3_BUCKET_NAME}/*",
            ],
        }],
    }
    iam.put_role_policy(
        RoleName="CapstoneRedshiftCopyRole",
        PolicyName="CapstoneRedshiftCopyPolicy",
        PolicyDocument=json.dumps(policy_doc),
    )
    print("Attached least-privilege policy to CapstoneRedshiftCopyRole")
    return role_arn


if __name__ == "__main__":
    lambda_arn = create_lambda_ingestion_role()
    glue_arn = create_glue_role()
    redshift_arn = create_redshift_copy_role()
    print(json.dumps({
        "lambda_role_arn": lambda_arn,
        "glue_role_arn": glue_arn,
        "redshift_role_arn": redshift_arn,
    }, indent=2))
