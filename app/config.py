from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str

    HOST: str
    PORT: int = Field(ge=1, le=65535)

    DEBUG: bool

    OLLAMA_MODEL: str
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_EMBEDDING_MODEL: str = "embeddinggemma"

    DB_HOST: str
    DB_PORT: int = Field(default=5432, ge=1, le=65535)
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: SecretStr

    QDRANT_URL: str = "http://127.0.0.1:6333"
    QDRANT_API_KEY: SecretStr | None = None
    QDRANT_COLLECTION: str = "medical_knowledge"

    KNOWLEDGE_ADMIN_API_KEY: SecretStr = Field(min_length=32)

    RAG_TOP_K: int = Field(default=4, ge=1, le=10)

    JWT_SECRET_KEY: SecretStr
    AUTH_BOOTSTRAP_TOKEN: SecretStr

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()