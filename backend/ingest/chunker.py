"""Herbalism RAG — Sentence-Aware Text Chunker.

Splits long text into overlapping chunks of approximately ``max_tokens``
words each, respecting sentence boundaries.  Used by all ingesters to
prepare source text for embedding and storage in ChromaDB.

**Tokenization**: Uses whitespace splitting (``len(text.split())``) per
BLU-002 §7 — no external tokenizer dependency needed.

**Overlap strategy**: The last ``overlap_tokens`` words of each chunk are
prepended to the next chunk, ensuring semantic continuity across chunk
boundaries.
"""

from __future__ import annotations

import re


# Pre-compiled pattern for sentence-boundary splitting.
# Splits on '. ', '? ', '! ' while keeping the delimiter with the preceding
# sentence (via lookbehind).
_SENTENCE_SPLIT: re.Pattern[str] = re.compile(r"(?<=[.!?])\s+")


def _token_count(text: str) -> int:
    """Count tokens using whitespace splitting.

    Args:
        text: Input text.

    Returns:
        Number of whitespace-delimited tokens.
    """
    return len(text.split())


def chunk_text(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    min_tokens: int = 100,
) -> list[str]:
    """Split text into overlapping chunks at sentence boundaries.

    Sentences are accumulated until adding the next sentence would
    exceed ``max_tokens``.  At that point the accumulated text becomes
    a chunk, and the next chunk starts with the last ``overlap_tokens``
    words of the previous chunk for continuity.

    Args:
        text: The source text to chunk.
        max_tokens: Maximum tokens (words) per chunk.
        overlap_tokens: Number of trailing tokens to carry into the
            next chunk.
        min_tokens: Minimum tokens for a chunk to be kept.  Fragments
            shorter than this are discarded.

    Returns:
        List of text chunks.  May be empty if the input is too short
        after filtering.
    """
    if not text or not text.strip():
        return []

    sentences: list[str] = _split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_tokens: int = 0

    for sentence in sentences:
        sentence_tokens: int = _token_count(sentence)

        if current_tokens + sentence_tokens > max_tokens and current_sentences:
            chunk_text_str: str = " ".join(current_sentences).strip()
            chunks.append(chunk_text_str)

            # Build overlap from the tail of the current chunk
            overlap_sentences: list[str] = _get_overlap(
                current_sentences, overlap_tokens
            )
            current_sentences = overlap_sentences
            current_tokens = _token_count(" ".join(current_sentences))

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Flush remaining sentences
    if current_sentences:
        remaining: str = " ".join(current_sentences).strip()
        if remaining:
            chunks.append(remaining)

    # Filter out chunks shorter than min_tokens
    return [c for c in chunks if _token_count(c) >= min_tokens]


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences at '. ', '? ', '! ' boundaries.

    Preserves sentence-ending punctuation with the sentence.  Strips
    each sentence and discards empty fragments.

    Args:
        text: Raw input text.

    Returns:
        List of non-empty sentence strings.
    """
    raw: list[str] = _SENTENCE_SPLIT.split(text.strip())
    return [s.strip() for s in raw if s.strip()]


def _get_overlap(
    sentences: list[str],
    overlap_tokens: int,
) -> list[str]:
    """Extract trailing sentences totalling approximately overlap_tokens.

    Walks backward through the sentence list, accumulating sentences
    until the token target is met.

    Args:
        sentences: List of sentences from the current chunk.
        overlap_tokens: Target number of overlap tokens.

    Returns:
        List of sentences forming the overlap prefix for the next chunk.
    """
    overlap: list[str] = []
    tokens_collected: int = 0

    for sentence in reversed(sentences):
        sentence_tokens: int = _token_count(sentence)
        if tokens_collected + sentence_tokens > overlap_tokens and overlap:
            break
        overlap.insert(0, sentence)
        tokens_collected += sentence_tokens

    return overlap
