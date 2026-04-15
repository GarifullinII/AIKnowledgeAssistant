import json
from app.core.config import settings
from app.services.openai_service import client, run_with_openai_retry


def rerank_chunks(question: str, candidate_chunks: list[dict], top_n: int = 3) -> list[dict]:
    if not candidate_chunks:
        return []

    numbered_chunks = []
    for idx, chunk in enumerate(candidate_chunks, start=1):
        numbered_chunks.append(
            {
                "rank_id": idx,
                "chunk_id": chunk["chunk_id"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"][:1200],
                "similarity": chunk.get("similarity", 0.0),
            }
        )

    prompt = f"""
Ты ранжируешь фрагменты документов по полезности для ответа на вопрос.

Вопрос:
{question}

Фрагменты:
{json.dumps(numbered_chunks, ensure_ascii=False, indent=2)}

Задача:
1. Выбери самые полезные фрагменты для ответа на вопрос.
2. Отсортируй их от самого полезного к менее полезному.
3. Верни JSON-массив только из rank_id.
4. Не добавляй пояснений.

Пример ответа:
[3, 1, 2]
"""

    response = run_with_openai_retry(
        lambda: client.responses.create(
            model=settings.openai_chat_model,
            input=prompt,
        ),
        action_name="chunk rerank",
    )

    output_text = response.output_text.strip()

    try:
        reranked_ids = json.loads(output_text)
    except Exception:
        return candidate_chunks[:top_n]

    id_to_chunk = {idx + 1: chunk for idx, chunk in enumerate(candidate_chunks)}

    reranked_chunks = []
    for rank_id in reranked_ids:
        chunk = id_to_chunk.get(rank_id)
        if chunk:
            reranked_chunks.append(chunk)

    if not reranked_chunks:
        return candidate_chunks[:top_n]

    return reranked_chunks[:top_n]
