"""
AWS Glue ETL job (PySpark), deployed as a Glue job script.

Reads newly-catalogued CSV/JSON data via the Glue Data Catalog, performs:
  1. Data normalization (column name standardization, type coercion)
  2. Schema validation (required-field presence check, logged to
     glue_catalog_metadata table for the AI query layer's governance queries)
  3. Systematic load into Redshift structured_data / customer_metrics tables

Run this as a Glue job (Glue console / start_job_run), not as a plain
script -- it depends on the Glue runtime's awsglue module and Spark context.
"""
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, lower, trim, current_timestamp
from pyspark.sql.types import StringType

args = getResolvedOptions(sys.argv, ["JOB_NAME", "GLUE_DATABASE", "REDSHIFT_CONNECTION",
                                      "REDSHIFT_TEMP_DIR", "SOURCE_S3_KEY"])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# Required metadata fields our data governance policy mandates for any
# ingested structured dataset. Used both for schema validation here and
# for the "missing required metadata fields" synthesis query later.
REQUIRED_FIELDS = {"record_date", "source_system", "record_id"}


def normalize_columns(df):
    for c in df.columns:
        df = df.withColumnRenamed(c, c.strip().lower().replace(" ", "_"))
    return df


def validate_schema(df, dataset_name: str):
    """Logs which required fields are present/missing for this dataset."""
    present_columns = set(df.columns)
    rows = []
    for field in REQUIRED_FIELDS:
        rows.append((dataset_name, field, "STRING", True, field in present_columns))
    validation_df = spark.createDataFrame(
        rows, ["dataset_name", "column_name", "data_type", "is_required_field", "is_present"]
    )
    return validation_df


def load_to_redshift(df, table_name: str):
    dynamic_frame = DynamicFrame.fromDF(df, glueContext, table_name)
    glueContext.write_dynamic_frame.from_jdbc_conf(
        frame=dynamic_frame,
        catalog_connection=args["REDSHIFT_CONNECTION"],
        connection_options={"dbtable": table_name, "database": "capstone_warehouse"},
        redshift_tmp_dir=args["REDSHIFT_TEMP_DIR"],
    )


def main():
    source_key = args["SOURCE_S3_KEY"]
    dataset_name = source_key.split("/")[-1]

    catalog_table = args["GLUE_DATABASE"]
    dyf = glueContext.create_dynamic_frame.from_catalog(
        database=args["GLUE_DATABASE"], table_name=catalog_table
    )
    df = dyf.toDF()

    df = normalize_columns(df)
    df = df.withColumn("ingested_at", current_timestamp())

    validation_df = validate_schema(df, dataset_name)
    load_to_redshift(validation_df, "glue_catalog_metadata")

    load_to_redshift(df, "structured_data")

    print(f"ETL complete for {dataset_name}: "
          f"{df.count()} rows loaded, schema validated against {REQUIRED_FIELDS}")

    job.commit()


if __name__ == "__main__":
    main()
