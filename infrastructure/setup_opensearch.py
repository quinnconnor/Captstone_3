"""
Creates the OpenSearch k-NN index used for storing Sentence Transformers
embeddings and performing semantic search over document chunks.
"""
from opensearchpy import OpenSearch, RequestsHttpConnection

from config import (
    OPENSEARCH_HOST, OPENSEARCH_PORT, OPENSEARCH_INDEX,
    OPENSEARCH_USER, OPENSEARCH_PASSWORD,
)
from embeddings.embedder import get_embedding_dimension


def get_client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def create_index():
    client = get_client()
    dim = get_embedding_dimension()  # 384 for all-MiniLM-L6-v2

    if client.indices.exists(index=OPENSEARCH_INDEX):
        print(f"Index '{OPENSEARCH_INDEX}' already exists.")
        return

    index_body = {
        "settings": {
            "index": {"knn": True, "knn.algo_param.ef_search": 100}
        },
        "mappings": {
            "properties": {
                "document_id": {"type": "integer"},
                "s3_key": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "chunk_text": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib",
                    },
                },
            }
        },
    }
    client.indices.create(index=OPENSEARCH_INDEX, body=index_body)
    print(f"Created OpenSearch index '{OPENSEARCH_INDEX}' with dimension {dim}")


if __name__ == "__main__":
    create_index()
