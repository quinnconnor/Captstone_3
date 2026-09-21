"""
Lambda handler triggered on S3 upload under raw/csv/ or raw/json/.

Rather than parsing structured files itself, this Lambda's job is workflow
automation: it starts the Glue Crawler (to catalog/discover schema for the
new file) and then starts the Glue ETL job (normalize, validate, load into
Redshift). This keeps heavy ETL logic in Glue, where it belongs, and keeps
the Lambda thin and fast.
"""
import json
import os
import sys

import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AWS_REGION, GLUE_CRAWLER_NAME, GLUE_ETL_JOB_NAME

glue = boto3.client("glue", region_name=AWS_REGION)


def start_crawler_if_idle():
    state = glue.get_crawler(Name=GLUE_CRAWLER_NAME)["Crawler"]["State"]
    if state == "READY":
        glue.start_crawler(Name=GLUE_CRAWLER_NAME)
        print(f"Started crawler {GLUE_CRAWLER_NAME}")
    else:
        print(f"Crawler {GLUE_CRAWLER_NAME} already in state {state}; skipping start.")


def start_etl_job(s3_key: str):
    response = glue.start_job_run(
        JobName=GLUE_ETL_JOB_NAME,
        Arguments={"--SOURCE_S3_KEY": s3_key},
    )
    print(f"Started ETL job {GLUE_ETL_JOB_NAME}, run id={response['JobRunId']}")
    return response["JobRunId"]


def lambda_handler(event, context):
    job_runs = []
    for record in event.get("Records", []):
        key = record["s3"]["object"]["key"]
        print(f"New structured file detected: {key}")
        start_crawler_if_idle()
        job_run_id = start_etl_job(key)
        job_runs.append({"s3_key": key, "glue_job_run_id": job_run_id})

    return {"statusCode": 200, "body": json.dumps(job_runs)}
