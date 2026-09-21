"""
Local document embedder using Sentence Transformers.

IMPLEMENTATION NOTE (confirmed in sandbox testing):
Both Bedrock embedding model families were tested directly against this
account and both are denied:
    - amazon.titan-embed-text-v2:0
    - cohere.embed-english-v3
This is a structural gap in the sandbox's Bedrock permissions (the
embeddings capability itself, not a specific model), so switching to a
different Bedrock embedding model would not help. Sentence Transformers
runs entirely locally, needs no API key or network call, and produces
the same kind of dense embedding vector OpenSearch needs for its k-NN
index. Bedrock (Claude) is still used for text generation in the AI
query layer -- that call path is confirmed working.
"""
from functools import lru_cache
from sentence_transformers import SentenceTransformer

from config import SENTENCE_TRANSFORMER_MODEL


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)


def embed_text(text: str) -> list:
    """Return a single embedding vector (list[float]) for one string."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: list) -> list:
    """Return a list of embedding vectors for a list of strings."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vectors]


def get_embedding_dimension() -> int:
    model = _get_model()
    return model.get_sentence_embedding_dimension()


if __name__ == "__main__":
    vec = embed_text("Customer churn rate increased in Q3.")
    print(f"Embedding dimension: {len(vec)}")
    print(f"First 5 values: {vec[:5]}")
