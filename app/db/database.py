from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("documents")}
    statements: list[str] = []

    if "processing_status" not in existing_columns:
        statements.append(
            "ALTER TABLE documents ADD COLUMN processing_status VARCHAR NOT NULL DEFAULT 'queued'"
        )
    if "processing_error" not in existing_columns:
        statements.append("ALTER TABLE documents ADD COLUMN processing_error TEXT")
    if "source" not in existing_columns:
        statements.append("ALTER TABLE documents ADD COLUMN source VARCHAR")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
