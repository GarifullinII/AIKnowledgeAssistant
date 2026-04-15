from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from app.core.config import settings
from app.db.database import SessionLocal
from app.services.rag_service import ask_rag
from app.services.document_query_service import get_latest_documents


def format_documents_message(documents: list[dict]) -> str:
    if not documents:
        return "Документы пока не загружены."

    lines = ["Последние документы:"]
    for doc in documents:
        lines.append(f"- {doc['filename']} | id={doc['id']}")
    return "\n".join(lines)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Привет! Я AIKnowledgeAssistant Bot.\n\n"
        "Команды:\n"
        "/documents — показать последние документы\n"
        "/ask <вопрос> — задать вопрос\n\n"
        "Если TELEGRAM_DEFAULT_DOCUMENT_ID задан, бот будет спрашивать по нему.\n"
        "Иначе поиск пойдет по всем документам."
    )
    await update.message.reply_text(text)


async def documents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        documents = get_latest_documents(db, limit=10)
        await update.message.reply_text(format_documents_message(documents))
    finally:
        db.close()


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /ask ваш вопрос")
        return

    question = " ".join(context.args).strip()
    db = SessionLocal()
    try:
        document_id = settings.telegram_default_document_id or None

        result = ask_rag(
            question=question,
            document_id=document_id,
            db=db,
        )

        snippets = result.get("snippets", [])
        snippets_text = "\n\n".join(
            f"Snippet {idx + 1}: {snippet[:200]}"
            for idx, snippet in enumerate(snippets[:2])
        )

        final_text = f"Ответ:\n{result['answer']}"
        if snippets_text:
            final_text += f"\n\nИсточники:\n{snippets_text}"

        await update.message.reply_text(final_text[:4000])
    finally:
        db.close()


async def fallback_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я понимаю команды:\n"
        "/documents\n"
        "/ask <вопрос>"
    )


def main():
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("documents", documents_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_message))

    print("Telegram bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()