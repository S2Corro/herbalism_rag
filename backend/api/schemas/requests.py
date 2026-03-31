"""Herbalism RAG — API Request Schemas.

Pydantic models for validating incoming API request bodies.

- ``QueryRequest`` — validates the user's natural-language question
  for ``POST /api/query``.
"""

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    """Request body for ``POST /api/query``.

    Validates that the user's question is non-empty, stripped of leading/
    trailing whitespace, and within a reasonable length (3–1000 characters).

    Attributes:
        question: The natural-language question to answer using the RAG
            pipeline.  Must be between 3 and 1000 characters after
            whitespace stripping.

    Examples:
        >>> QueryRequest(question="What helps with stress?")
        QueryRequest(question='What helps with stress?')
    """

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural-language question (3–1000 chars)",
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        """Strip whitespace and reject blank questions.

        Args:
            v: Raw question string from the request body.

        Returns:
            The stripped, validated question string.

        Raises:
            ValueError: If the question is blank after stripping.
        """
        stripped: str = v.strip()
        if not stripped:
            raise ValueError("Question must not be blank")
        return stripped
