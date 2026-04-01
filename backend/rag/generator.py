"""Herbalism RAG — GeneratorService.

Sends a user question plus retrieved ``HerbChunk`` excerpts to Claude
Haiku and returns the synthesized answer with inline citation markers
(e.g. ``[1]``, ``[2]``).

Prompt design follows **BLU-002 §4** exactly:

* **System prompt** — instructs Claude to answer *only* from the
  provided sources and cite each claim with ``[N]`` brackets.
* **User prompt**  — contains the question followed by numbered source
  excerpts with title, source type, and year.

This service sits in the **Service Layer** (BLU-001 §2) and makes no
direct database calls — all retrieval is done by ``RetrieverService``
before this class is invoked.

Blueprints:
    BLU-002 §4 — Claude prompt design
    BLU-002 §5 — Response schema
"""

from __future__ import annotations

import time

import anthropic
import structlog

from backend.models.herb_chunk import HerbChunk

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Prompt templates (BLU-002 §4)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT: str = (
    "You are a herbalism research assistant. Answer questions using ONLY the "
    "provided source excerpts. For every factual claim, cite the source number "
    "in brackets like [1] or [2]. Do not add information not present in the "
    "sources. If the sources do not contain enough information to answer "
    "fully, say so explicitly."
)

NO_SOURCES_MESSAGE: str = (
    "No relevant sources found. Please try a different question or "
    "check that the knowledge base has been populated."
)


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------


class GeneratorAPIError(Exception):
    """Raised when the Anthropic API call fails."""


class GeneratorAuthError(GeneratorAPIError):
    """Raised on authentication / invalid-key errors from Anthropic."""


class GeneratorRateLimitError(GeneratorAPIError):
    """Raised when Anthropic returns a rate-limit error."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GeneratorService:
    """Synthesizes answers from HerbChunks using Claude Haiku.

    Builds a prompt matching BLU-002 §4, sends it to the Anthropic
    Messages API, and returns the text content of Claude's response.

    Args:
        api_key: Anthropic API key.
        model: Anthropic model identifier.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-20240307",
    ) -> None:
        """Initialize the Anthropic async client.

        Args:
            api_key: Anthropic API key.
            model: Anthropic model identifier.
        """
        self._client: anthropic.AsyncAnthropic = anthropic.AsyncAnthropic(
            api_key=api_key,
        )
        self._model: str = model

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def build_user_prompt(
        question: str,
        chunks: list[HerbChunk],
    ) -> str:
        """Build the user-side prompt with numbered source excerpts.

        Format matches BLU-002 §4::

            Question: {question}

            Sources:
            [1] {title} ({source_type}, {year})
            {text}

            [2] ...

        Args:
            question: The user's natural-language question.
            chunks: Retrieved ``HerbChunk`` objects to include.

        Returns:
            The formatted user prompt string.
        """
        sources_block: str = "\n\n".join(
            f"[{i}] {c.title} ({c.source_type}, {c.year})\n{c.text}"
            for i, c in enumerate(chunks, start=1)
        )
        return f"Question: {question}\n\nSources:\n{sources_block}"

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    async def synthesize(
        self,
        question: str,
        chunks: list[HerbChunk],
    ) -> str:
        """Send question + chunks to Claude and return the cited answer.

        If ``chunks`` is empty, returns a no-sources message immediately
        *without* making an API call.

        Args:
            question: The user's question.
            chunks: Retrieved source chunks (may be empty).

        Returns:
            The synthesized answer text with inline ``[N]`` citations.

        Raises:
            GeneratorAuthError: On authentication failures.
            GeneratorRateLimitError: On rate-limit responses.
            GeneratorAPIError: On any other Anthropic API error.
        """
        if not chunks:
            logger.info(
                "generator_no_sources",
                question_length=len(question),
            )
            return NO_SOURCES_MESSAGE

        user_prompt: str = self.build_user_prompt(question, chunks)

        start: float = time.monotonic()
        try:
            response: anthropic.types.Message = (
                await self._client.messages.create(
                    model=self._model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": user_prompt},
                    ],
                )
            )
        except anthropic.AuthenticationError as exc:
            raise GeneratorAuthError(
                f"Anthropic authentication failed: {exc}"
            ) from exc
        except anthropic.RateLimitError as exc:
            raise GeneratorRateLimitError(
                f"Anthropic rate limit exceeded: {exc}"
            ) from exc
        except anthropic.APIError as exc:
            raise GeneratorAPIError(
                f"Anthropic API error: {exc}"
            ) from exc

        elapsed_ms: int = int((time.monotonic() - start) * 1000)

        # Extract text from the first content block
        answer: str = response.content[0].text  # type: ignore[union-attr]

        logger.info(
            "generator_synthesize",
            question_length=len(question),
            chunk_count=len(chunks),
            elapsed_ms=elapsed_ms,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return answer
