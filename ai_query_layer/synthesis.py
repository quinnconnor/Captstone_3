"""
Handles the "both" routing case: questions that require combining a
Redshift structured-data fact with OpenSearch document context into a
single synthesized answer that cites both sources -- not two separate
answers, and not just whichever source was checked first.
"""
from ai_query_layer.sql_generator import generate_sql
from ai_query_layer.redshift_executor import execute_validated_query, SQLValidationError
from ai_query_layer.rag_responder import retrieve_relevant_chunks, _format_context
from ai_query_layer.bedrock_client import invoke_claude

SYNTHESIS_PROMPT_TEMPLATE = """You are answering a question that requires combining two sources:

1. STRUCTURED DATA (from the Redshift data warehouse):
{structured_data}

2. DOCUMENT CONTEXT (from company policy/strategy documents):
{document_context}

Write ONE unified answer that directly addresses the question by combining
both sources -- do not answer them separately. Explicitly state whether the
structured data aligns with, or is missing something required by, the
document context. Cite the structured data as [source: Redshift] and each
document excerpt as [source: s3_key, chunk N].

Question: {question}

Unified answer:"""


def answer_synthesis_query(question: str, top_k_chunks: int = 5) -> dict:
    # 1. Structured side: generate + validate + execute SQL.
    sql = generate_sql(question)
    try:
        rows = execute_validated_query(sql)
        structured_summary = f"SQL: {sql}\nResults: {rows}"
    except SQLValidationError as e:
        rows = []
        structured_summary = f"SQL: {sql}\nExecution blocked by validator: {e}"

    # 2. Document side: retrieve relevant chunks.
    chunks = retrieve_relevant_chunks(question, top_k=top_k_chunks)
    document_context = _format_context(chunks) if chunks else "No relevant document context found."

    # 3. Combine into one answer.
    prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        structured_data=structured_summary,
        document_context=document_context,
        question=question,
    )
    result = invoke_claude(prompt, max_tokens=700, call_type="contextual_response")

    return {
        "answer": result["text"],
        "sql_used": sql,
        "redshift_rows": rows,
        "document_sources": [
            {"s3_key": c["s3_key"], "chunk_index": c["chunk_index"]} for c in chunks
        ],
    }


if __name__ == "__main__":
    result = answer_synthesis_query(
        "Does our current customer churn rate (from the data warehouse) align "
        "with what our documented retention strategy says we should be seeing?"
    )
    print(result["answer"])
