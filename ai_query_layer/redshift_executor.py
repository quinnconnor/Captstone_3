"""
Executes a validated SQL query against Redshift and returns rows as a
list of dicts. This module never calls Bedrock or generates SQL itself --
it strictly executes what's handed to it, and only after the caller has
run it through ai_query_layer.sql_validator.validate_sql().
"""
from infrastructure.setup_redshift import get_connection
from ai_query_layer.sql_validator import validate_sql


class SQLValidationError(Exception):
    pass


def execute_validated_query(sql: str) -> list:
    validation = validate_sql(sql)
    if not validation["valid"]:
        raise SQLValidationError(f"Refusing to execute query: {validation['reason']}")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        execute_validated_query("DROP TABLE structured_data")
    except SQLValidationError as e:
        print(f"Correctly blocked: {e}")
