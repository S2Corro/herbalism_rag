"""Herbalism RAG — Application Configuration.

Reads configuration from environment variables and .env file using
pydantic-settings BaseSettings. All settings are typed and validated
at startup. If ANTHROPIC_API_KEY is missing or empty, the application
fails fast with a clear ValueError — no silent None, no runtime
surprise.

Usage:
    from backend.config import settings
    print(settings.anthropic_api_key)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    This class uses pydantic-settings to read configuration values from
    environment variables (and optionally a .env file located at the project
    root). All fields are typed and have sensible defaults except for
    ``anthropic_api_key``, which is required and will raise a ``ValueError``
    if not set.

    Attributes:
        anthropic_api_key: Anthropic API key for Claude LLM calls.
        chroma_db_path: Filesystem path for the persistent ChromaDB store.
        collection_name: Name of the ChromaDB collection for herb chunks.
        embedding_model: HuggingFace model ID for local sentence embeddings.
        llm_model: Anthropic model identifier for generation.
        top_k: Number of nearest-neighbor chunks to retrieve per query.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    anthropic_api_key: str = ""
    chroma_db_path: str = "data/chroma_db"
    collection_name: str = "herbalism"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model: str = "claude-haiku-4-5-20251001"
    top_k: int = 8

    @field_validator("anthropic_api_key")
    @classmethod
    def api_key_must_not_be_empty(cls, value: str) -> str:
        """Validate that the Anthropic API key is present and non-empty.

        Args:
            value: The raw value read from environment/config.

        Returns:
            The validated, non-empty API key string.

        Raises:
            ValueError: If the key is missing, empty, or still the placeholder.
        """
        if not value or value.strip() == "" or value == "your-anthropic-api-key-here":
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Copy .env.example to .env and add your key."
            )
        return value


# Module-level singleton — imported by other modules as:
#   from backend.config import settings
settings: Settings = Settings()
