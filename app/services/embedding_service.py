from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)


def get_text_embedding(text: str) -> list[float]:
    clean_text = text.strip()
    if not clean_text:
        return []

    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=clean_text
    )

    return response.data[0].embedding