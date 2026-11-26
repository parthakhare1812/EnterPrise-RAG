
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Enterprise RAG"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    API_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    DATABASE_PATH: Path = PROJECT_ROOT / "data" / "enterprise_rag.db"
    FAISS_INDEX_PATH: Path = PROJECT_ROOT / "data" / "faiss_index"
    CHECKPOINT_DB_PATH: Path = PROJECT_ROOT / "data" / "checkpoints.db"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = ""

    EMBEDDING_MODEL: str = "local-feature-hashing"
    EMBEDDING_DIMENSIONS: int = 384

    UPLOAD_DIR: Path = PROJECT_ROOT / "data" / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".docx", ".txt"]

    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200

    RETRIEVAL_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.35

    LANGGRAPH_CHECKPOINT_ENABLED: bool = True

    def validate_settings(self) -> None:
        if self.EMBEDDING_MODEL != "local-feature-hashing":
            raise ValueError(
                "This retrieval-only configuration requires "
                "EMBEDDING_MODEL=local-feature-hashing."
            )

        if self.EMBEDDING_DIMENSIONS != 384:
            raise ValueError(
                "local-feature-hashing requires "
                "EMBEDDING_DIMENSIONS=384."
            )

        if self.CHUNK_SIZE <= 0:
            raise ValueError(
                "CHUNK_SIZE must be greater than zero."
            )

        if self.CHUNK_OVERLAP < 0:
            raise ValueError(
                "CHUNK_OVERLAP cannot be negative."
            )

        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError(
                "CHUNK_OVERLAP must be smaller than CHUNK_SIZE."
            )

        if self.RETRIEVAL_TOP_K <= 0:
            raise ValueError(
                "RETRIEVAL_TOP_K must be greater than zero."
            )

        if not 0 <= self.SIMILARITY_THRESHOLD <= 1:
            raise ValueError(
                "SIMILARITY_THRESHOLD must be between 0 and 1."
            )

        if self.MAX_UPLOAD_SIZE_MB <= 0:
            raise ValueError(
                "MAX_UPLOAD_SIZE_MB must be greater than zero."
            )

        if not self.API_PREFIX.startswith("/"):
            raise ValueError(
                "API_PREFIX must start with '/'."
            )

        if not self.ALLOWED_EXTENSIONS:
            raise ValueError(
                "At least one allowed upload extension is required."
            )

        self.ALLOWED_EXTENSIONS = [
            extension.lower()
            if extension.startswith(".")
            else f".{extension.lower()}"
            for extension in self.ALLOWED_EXTENSIONS
        ]

    def create_directories(self) -> None:
        directories = [
            self.DATABASE_PATH.parent,
            self.FAISS_INDEX_PATH,
            self.CHECKPOINT_DB_PATH.parent,
            self.UPLOAD_DIR,
        ]

        for directory in directories:
            directory.mkdir(
                parents=True,
                exist_ok=True
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    configuration = Settings()
    configuration.validate_settings()
    configuration.create_directories()
    return configuration


settings = get_settings()
