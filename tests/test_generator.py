# ---
# title: "Unit Tests — GeneratorService"
# sprint: SPR-004
# task: T-004
# author: Developer Agent B
# ---
"""Unit tests for the GeneratorService.

All Anthropic API calls are mocked — no real Claude calls in tests.
Tests verify prompt construction (BLU-002 §4 format), synthesize
behavior, empty-chunks handling, and API error propagation.
"""

import os

os.environ["ANTHROPIC_API_KEY"] = "test-fake-key-for-unit-tests"

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.herb_chunk import HerbChunk
from backend.rag.generator import (
    NO_SOURCES_MESSAGE,
    SYSTEM_PROMPT,
    GeneratorAPIError,
    GeneratorAuthError,
    GeneratorRateLimitError,
    GeneratorService,
)

# -----------------------------------------------------------------------
# Shared helpers
# -----------------------------------------------------------------------

FAKE_API_KEY: str = "sk-fake-test-key"


def _make_chunks() -> list[HerbChunk]:
    """Create test HerbChunks for prompt construction tests."""
    return [
        HerbChunk(
            id="pubmed-1-chunk-0",
            text="Ashwagandha reduced cortisol levels.",
            source_type="PubMed",
            title="Cortisol Study",
            url="https://pubmed.ncbi.nlm.nih.gov/1/",
            year="2020",
            herbs=["Ashwagandha"],
            chunk_index=0,
        ),
        HerbChunk(
            id="who-2-chunk-0",
            text="Holy basil has adaptogenic effects.",
            source_type="WHO",
            title="WHO Basil Monograph",
            url="https://who.int/basil",
            year="2018",
            herbs=["Holy Basil"],
            chunk_index=0,
        ),
    ]


def _mock_anthropic_response(text: str = "Test answer [1].") -> MagicMock:
    """Build a mock Anthropic Message response."""
    content_block = MagicMock()
    content_block.text = text

    usage = MagicMock()
    usage.input_tokens = 100
    usage.output_tokens = 50

    response = MagicMock()
    response.content = [content_block]
    response.usage = usage
    return response


# -----------------------------------------------------------------------
# Prompt construction
# -----------------------------------------------------------------------


class TestBuildUserPrompt:
    """Tests for the static prompt builder matching BLU-002 §4 format."""

    def test_prompt_includes_question(self) -> None:
        """The user prompt should start with the question."""
        prompt: str = GeneratorService.build_user_prompt(
            "What helps cortisol?", _make_chunks()
        )
        assert "Question: What helps cortisol?" in prompt

    def test_prompt_includes_numbered_sources(self) -> None:
        """Sources should be numbered [1], [2], etc."""
        prompt: str = GeneratorService.build_user_prompt(
            "test", _make_chunks()
        )
        assert "[1] Cortisol Study (PubMed, 2020)" in prompt
        assert "[2] WHO Basil Monograph (WHO, 2018)" in prompt

    def test_prompt_includes_source_text(self) -> None:
        """Source text should appear after each header."""
        prompt: str = GeneratorService.build_user_prompt(
            "test", _make_chunks()
        )
        assert "Ashwagandha reduced cortisol levels." in prompt
        assert "Holy basil has adaptogenic effects." in prompt

    def test_prompt_includes_sources_label(self) -> None:
        """The prompt should contain a 'Sources:' section header."""
        prompt: str = GeneratorService.build_user_prompt(
            "test", _make_chunks()
        )
        assert "Sources:" in prompt


# -----------------------------------------------------------------------
# Synthesize
# -----------------------------------------------------------------------


class TestSynthesize:
    """Tests for the synthesize() async method."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_answer_text(self) -> None:
        """synthesize() should return the text from Claude's response."""
        service = GeneratorService(api_key=FAKE_API_KEY)
        mock_response = _mock_anthropic_response("Ashwagandha helps [1].")

        with patch.object(
            service._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            answer: str = await service.synthesize(
                "What helps cortisol?", _make_chunks()
            )

        assert answer == "Ashwagandha helps [1]."

    @pytest.mark.asyncio
    async def test_synthesize_empty_chunks_no_api_call(self) -> None:
        """Empty chunks should return NO_SOURCES_MESSAGE without API call."""
        service = GeneratorService(api_key=FAKE_API_KEY)

        with patch.object(
            service._client.messages,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            answer: str = await service.synthesize("test question", [])

        assert answer == NO_SOURCES_MESSAGE
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_synthesize_sends_system_prompt(self) -> None:
        """The API call should use the BLU-002 §4 system prompt."""
        service = GeneratorService(api_key=FAKE_API_KEY)
        mock_response = _mock_anthropic_response("answer")

        with patch.object(
            service._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_create:
            await service.synthesize("question", _make_chunks())

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["system"] == SYSTEM_PROMPT
        assert call_kwargs["max_tokens"] == 1024


# -----------------------------------------------------------------------
# Error handling
# -----------------------------------------------------------------------


class TestGeneratorErrors:
    """Tests for Anthropic API error handling."""

    @pytest.mark.asyncio
    async def test_auth_error_raises_generator_auth_error(self) -> None:
        """AuthenticationError should be wrapped as GeneratorAuthError."""
        import anthropic

        service = GeneratorService(api_key=FAKE_API_KEY)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "invalid key"}}
        mock_response.headers = {}

        with patch.object(
            service._client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=anthropic.AuthenticationError(
                message="invalid key",
                response=mock_response,
                body={"error": {"message": "invalid key"}},
            ),
        ):
            with pytest.raises(GeneratorAuthError):
                await service.synthesize("test", _make_chunks())

    @pytest.mark.asyncio
    async def test_rate_limit_raises_generator_rate_limit_error(
        self,
    ) -> None:
        """RateLimitError should be wrapped as GeneratorRateLimitError."""
        import anthropic

        service = GeneratorService(api_key=FAKE_API_KEY)

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "rate limited"}}
        mock_response.headers = {}

        with patch.object(
            service._client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=anthropic.RateLimitError(
                message="rate limited",
                response=mock_response,
                body={"error": {"message": "rate limited"}},
            ),
        ):
            with pytest.raises(GeneratorRateLimitError):
                await service.synthesize("test", _make_chunks())
