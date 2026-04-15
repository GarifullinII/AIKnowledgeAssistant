from app.core.config import settings
from app.services.openai_service import client, run_with_openai_retry


def get_text_embedding(text: str) -> list[float]:
    clean_text = text.strip()
    if not clean_text:
        return []

    response = run_with_openai_retry(
        lambda: client.embeddings.create(
            model=settings.openai_embedding_model,
            input=clean_text,
        ),
        action_name="embedding generation",
    )

    return response.data[0].embedding
