from sqlalchemy.orm import Session
from app.db.models import Document


def get_latest_documents(db: Session, limit: int = 10) -> list[dict]:
    documents = (
        db.query(Document)
        .order_by(Document.uploaded_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": doc.uploaded_at,
            "preview": doc.preview,
        }
        for doc in documents
    ]