"""
Generates required BI charts (2+) from Redshift data using matplotlib,
saved as image files and uploaded to s3://<bucket>/charts/.
"""
import os
import boto3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import AWS_REGION, S3_BUCKET_NAME
from ai_query_layer.redshift_executor import execute_validated_query

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

s3 = boto3.client("s3", region_name=AWS_REGION)


def chart_churn_rate_over_time():
    rows = execute_validated_query(
        "SELECT metric_date, churn_rate FROM customer_metrics ORDER BY metric_date"
    )
    dates = [r["metric_date"] for r in rows]
    rates = [r["churn_rate"] for r in rows]

    plt.figure(figsize=(9, 5))
    plt.plot(dates, rates, marker="o", color="#2563eb")
    plt.title("Customer Churn Rate Over Time")
    plt.xlabel("Date")
    plt.ylabel("Churn Rate")
    plt.grid(alpha=0.3)
    plt.tight_layout()

    path = os.path.join(OUTPUT_DIR, "churn_rate_over_time.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def chart_dataset_metadata_completeness():
    rows = execute_validated_query(
        "SELECT dataset_name, SUM(CASE WHEN is_present THEN 1 ELSE 0 END) AS present_count, "
        "COUNT(*) AS required_count FROM glue_catalog_metadata GROUP BY dataset_name"
    )
    names = [r["dataset_name"] for r in rows]
    present = [r["present_count"] for r in rows]
    required = [r["required_count"] for r in rows]

    x = range(len(names))
    plt.figure(figsize=(9, 5))
    plt.bar(x, required, color="#e5e7eb", label="Required fields")
    plt.bar(x, present, color="#16a34a", label="Present fields")
    plt.xticks(x, names, rotation=30, ha="right")
    plt.title("Dataset Metadata Completeness (Glue Catalog)")
    plt.ylabel("Field count")
    plt.legend()
    plt.tight_layout()

    path = os.path.join(OUTPUT_DIR, "dataset_metadata_completeness.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def upload_chart(local_path: str):
    key = f"charts/{os.path.basename(local_path)}"
    s3.upload_file(local_path, S3_BUCKET_NAME, key)
    print(f"Uploaded {local_path} -> s3://{S3_BUCKET_NAME}/{key}")


if __name__ == "__main__":
    paths = [chart_churn_rate_over_time(), chart_dataset_metadata_completeness()]
    for p in paths:
        print(f"Generated chart: {p}")
        upload_chart(p)
