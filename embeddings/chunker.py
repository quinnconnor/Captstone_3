"""
Chunks raw extracted text (from Textract) into 500-1000 token windows,
splitting on paragraph/sentence boundaries where possible so chunks stay
semantically coherent for embedding + retrieval.

Token counting: tries tiktoken's cl100k_base encoding first (closest to
Claude's actual tokenization), but falls back to a dependency-free
heuristic (~4 chars/token, the standard English-text approximation) if
tiktoken's BPE file can't be loaded -- e.g. in a Lambda/sandbox with no
route to openaipublic.blob.core.windows.net. This keeps chunking usable
without requiring that specific outbound network call at runtime.
"""
import re

try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENCODER = None


def count_tokens(text: str) -> int:
    if _ENCODER is not None:
        return len(_ENCODER.encode(text))
    # Fallback heuristic: ~4 characters per token for English text.
    return max(1, len(text) // 4)


def _split_into_sentences(text: str):
    # Lightweight sentence splitter; avoids pulling in a heavy NLP dependency.
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s]


def chunk_text(text: str, min_tokens: int = 500, max_tokens: int = 1000):
    """
    Greedily packs sentences into chunks that stay within
    [min_tokens, max_tokens] wherever the source text allows it.

    Returns a list of dicts: {"chunk_index": int, "text": str, "token_count": int}
    """
    sentences = _split_into_sentences(text)
    chunks = []
    current_sentences = []
    current_tokens = 0
    chunk_index = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        # Single sentence bigger than max_tokens: flush current, emit it alone.
        if sentence_tokens > max_tokens:
            if current_sentences:
                chunks.append(_finalize_chunk(current_sentences, chunk_index))
                chunk_index += 1
                current_sentences, current_tokens = [], 0
            chunks.append(_finalize_chunk([sentence], chunk_index))
            chunk_index += 1
            continue

        if current_tokens + sentence_tokens > max_tokens and current_tokens >= min_tokens:
            chunks.append(_finalize_chunk(current_sentences, chunk_index))
            chunk_index += 1
            current_sentences, current_tokens = [], 0

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    if current_sentences:
        chunks.append(_finalize_chunk(current_sentences, chunk_index))

    return chunks


def _finalize_chunk(sentences, chunk_index):
    text = " ".join(sentences)
    return {
        "chunk_index": chunk_index,
        "text": text,
        "token_count": count_tokens(text),
    }


if __name__ == "__main__":
    sample = "This is sentence one. " * 400
    result = chunk_text(sample)
    print(f"Produced {len(result)} chunks")
    for c in result:
        print(c["chunk_index"], c["token_count"])
