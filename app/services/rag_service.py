from typing import Optional


def ask_rag(question: str, document_id: Optional[str] = None) -> dict:
    return {
        "answer": f"Stub answer for: {question}",
        "document_id": document_id,
        "snippets": []
    }
