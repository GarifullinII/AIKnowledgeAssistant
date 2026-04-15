from app.core.config import settings
from app.services.openai_service import client, run_with_openai_retry


def generate_answer(question: str, context_chunks: list[dict]) -> str:
    if not context_chunks:
        return "There is not enough data in the documents to answer the question."

    context = "\n\n".join(
        f"[Chunk {chunk['chunk_index']}]\n{chunk['text']}"
        for chunk in context_chunks
    )

    prompt = f"""
You are an assistant who responds only based on the context provided.

Правила:
1. Answer only according to the context below.
2. If there's not enough data, just say so.
3. Don't make up facts.
4. Reply in the language the user writes in: if the user writes in Russian, reply in Russian; if in English, reply in English.

Контекст:
{context}

Вопрос:
{question}
"""

    response = run_with_openai_retry(
        lambda: client.responses.create(
            model=settings.openai_chat_model,
            input=prompt,
        ),
        action_name="answer generation",
    )

    return response.output_text.strip()
