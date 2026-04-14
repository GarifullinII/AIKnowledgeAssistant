from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AIKnowledgeAssistant"
    app_version: str = "0.1.0"
    debug: bool = True

    upload_dir: str = "data/uploads"

    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4.1-mini"

    postgres_db: str = "aiknowledgeassistant"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: str = "redis://localhost:6379/0"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "document_chunks"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
