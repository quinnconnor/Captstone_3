"""
Creates the Glue Crawler that discovers schemas for all ingested CSV/JSON
files under s3://<bucket>/raw/{csv,json}/ and registers them in the Glue
Data Catalog. The AI query layer's synthesis queries later check this
catalog for required-metadata-field validation.
"""
import boto3

from config import AWS_REGION, S3_BUCKET_NAME, GLUE_DATABASE_NAME, GLUE_CRAWLER_NAME

glue = boto3.client("glue", region_name=AWS_REGION)


def create_database_if_missing():
    try:
        glue.create_database(DatabaseInput={"Name": GLUE_DATABASE_NAME})
        print(f"Created Glue database: {GLUE_DATABASE_NAME}")
    except glue.exceptions.AlreadyExistsException:
        print(f"Glue database already exists: {GLUE_DATABASE_NAME}")


def create_crawler(role_arn: str):
    try:
        glue.create_crawler(
            Name=GLUE_CRAWLER_NAME,
            Role=role_arn,
            DatabaseName=GLUE_DATABASE_NAME,
            Targets={
                "S3Targets": [
                    {"Path": f"s3://{S3_BUCKET_NAME}/raw/csv/"},
                    {"Path": f"s3://{S3_BUCKET_NAME}/raw/json/"},
                ]
            },
            SchemaChangePolicy={
                "UpdateBehavior": "UPDATE_IN_DATABASE",
                "DeleteBehavior": "LOG",
            },
            RecrawlPolicy={"RecrawlBehavior": "CRAWL_NEW_FOLDERS_ONLY"},
        )
        print(f"Created crawler: {GLUE_CRAWLER_NAME}")
    except glue.exceptions.AlreadyExistsException:
        print(f"Crawler already exists: {GLUE_CRAWLER_NAME}")


def run_crawler_now():
    glue.start_crawler(Name=GLUE_CRAWLER_NAME)
    print(f"Triggered crawler run: {GLUE_CRAWLER_NAME}")


if __name__ == "__main__":
    import sys
    role_arn = sys.argv[1] if len(sys.argv) > 1 else None
    create_database_if_missing()
    if role_arn:
        create_crawler(role_arn)
    else:
        print("Pass the Glue role ARN as an argument to create the crawler, "
              "e.g. python setup_glue_crawler.py arn:aws:iam::...:role/CapstoneGlueRole")
