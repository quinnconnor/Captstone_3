"""
For questions requiring OpenSearch (semantic/document search), retrieves
the top-k relevant chunks by embedding similarity, then asks Claude via
Bedrock to generate a grounded answer that cites its sources by document
key and chunk index.
"""
from embeddings.embedder import embed_text
from infrastructure.setup_opensearch import get_client as get_opensearch_client
from ai_query_layer.bedrock_client import invoke_claude
from config import OPENSEARCH_INDEX

RAG_PROMPT_TEMPLATE = """Answer the question using ONLY the source excerpts below.
Cite each fact you use by its [source: s3_key, chunk N] tag. If the excerpts
don't contain the answer, say so explicitly rather than guessing.

Source excerpts:
{context}

Question: {question}

Answer (with inline citations):"""


def retrieve_relevant_chunks(question: str, top_k: int = 5) -> list:
    query_vector = embed_text(question)
    client = get_opensearch_client()

    search_body = {
        "size": top_k,
        "query": {
            "knn": {"embedding": {"vector": query_vector, "k": top_k}}
        },
    }
    response = client.search(index=OPENSEARCH_INDEX, body=search_body)

    hits = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        hits.append({
            "s3_key": source["s3_key"],
            "chunk_index": source["chunk_index"],
            "chunk_text": source["chunk_text"],
            "score": hit["_score"],
        })
    return hits


def _format_context(chunks: list) -> str:
    lines = []
    for chunk in chunks:
        lines.append(
            f"[source: {chunk['s3_key']}, chunk {chunk['chunk_index']}]\n{chunk['chunk_text']}"
        )
    return "\n\n".join(lines)


def answer_from_documents(question: str, top_k: int = 5) -> dict:
    chunks = retrieve_relevant_chunks(question, top_k=top_k)
    if not chunks:
        return {
            "answer": "No relevant document context was found for this question.",
            "sources": [],
        }

    context = _format_context(chunks)
    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
    result = invoke_claude(prompt, max_tokens=600, call_type="contextual_response")

    return {
        "answer": result["text"],
        "sources": [{"s3_key": c["s3_key"], "chunk_index": c["chunk_index"]} for c in chunks],
    }


if __name__ == "__main__":
    print(answer_from_documents(
        "What does our documented retention strategy recommend for at-risk customers?"
    ))
