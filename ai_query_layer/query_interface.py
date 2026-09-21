"""
Top-level entry point for the AI query layer. Given a natural language
question, this:
  1. Routes it (router.route_query) to OpenSearch, Redshift, or both.
  2. For "redshift": generates SQL (sql_generator), validates it
     (sql_validator), and executes it (redshift_executor).
  3. For "opensearch": retrieves + generates a grounded, cited answer
     (rag_responder).
  4. For "both": runs the combined synthesis path (synthesis).

This is the module the CLI, tests, and (for the Gold stretch goal) the
API Gateway Lambda all call into.
"""
from ai_query_layer.router import route_query
from ai_query_layer.sql_generator import generate_sql
from ai_query_layer.redshift_executor import execute_validated_query, SQLValidationError
from ai_query_layer.rag_responder import answer_from_documents
from ai_query_layer.synthesis import answer_synthesis_query


def answer_question(question: str) -> dict:
    route = route_query(question)

    if route == "redshift":
        sql = generate_sql(question)
        try:
            rows = execute_validated_query(sql)
            return {
                "route": route, "question": question, "sql_used": sql,
                "answer": rows, "sources": ["Redshift"],
            }
        except SQLValidationError as e:
            return {
                "route": route, "question": question, "sql_used": sql,
                "answer": None, "error": str(e), "sources": ["Redshift"],
            }

    if route == "opensearch":
        result = answer_from_documents(question)
        return {
            "route": route, "question": question,
            "answer": result["answer"], "sources": result["sources"],
        }

    # route == "both"
    result = answer_synthesis_query(question)
    return {
        "route": route, "question": question,
        "answer": result["answer"], "sql_used": result["sql_used"],
        "sources": ["Redshift"] + result["document_sources"],
    }


if __name__ == "__main__":
    import json
    test_questions = [
        "What is the average churn rate for Q3 2026?",
        "What does our documented retention strategy recommend for at-risk customers?",
        "Does our current customer churn rate align with what our documented retention "
        "strategy says we should be seeing?",
    ]
    for q in test_questions:
        result = answer_question(q)
        print(json.dumps(result, indent=2, default=str))
        print("-" * 80)
