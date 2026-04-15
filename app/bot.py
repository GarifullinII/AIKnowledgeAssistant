from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.core.config import settings
from app.db.database import SessionLocal, ensure_runtime_schema
from app.services.cache_service import (
    clear_selected_document_id,
    get_selected_document_id,
    set_selected_document_id,
)
from app.services.document_query_service import get_latest_document, get_latest_documents
from app.services.document_service import get_document_by_id, save_telegram_document
from app.services.queue_service import enqueue_document_processing
from app.services.rag_service import ask_rag


def format_documents_message(documents: list[dict]) -> str:
    if not documents:
        return "Документы пока не загружены."

    lines = ["Последние документы:"]
    for doc in documents:
        status = doc.get("processing_status", "unknown")
        lines.append(f"- {doc['filename']} | id={doc['id']} | status={status}")
    return "\n".join(lines)


def get_active_document_id(chat_id: int | None) -> str | None:
    if chat_id is None:
        return settings.telegram_default_document_id or None
    return get_selected_document_id(chat_id) or settings.telegram_default_document_id or None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Привет! Я AIKnowledgeAssistant Bot.\n\n"
        "Команды:\n"
        "/documents — показать последние документы\n"
        "/use <document_id> — выбрать документ\n"
        "/use latest — выбрать последний документ\n"
        "/use all — искать по всем документам\n"
        "/selected — показать текущий выбор\n"
        "/ask <вопрос> — задать вопрос\n\n"
        "Также можно отправить PDF, TXT или MD файлом для загрузки."
    )
    await update.message.reply_text(text)


async def documents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        documents = get_latest_documents(db, limit=10)
        await update.message.reply_text(format_documents_message(documents))
    finally:
        db.close()


async def use_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        await update.message.reply_text("Не удалось определить чат.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /use <document_id|latest|all>")
        return

    raw_value = " ".join(context.args).strip()
    db = SessionLocal()
    try:
        if raw_value.lower() == "all":
            clear_selected_document_id(chat_id)
            await update.message.reply_text("Выбор документа сброшен. Поиск пойдет по всем документам.")
            return

        if raw_value.lower() == "latest":
            latest_document = get_latest_document(db)
            if not latest_document:
                await update.message.reply_text("Документы пока не загружены.")
                return

            set_selected_document_id(chat_id, latest_document["id"])
            await update.message.reply_text(
                "Выбран последний документ.\n"
                f"Файл: {latest_document['filename']}\n"
                f"id: {latest_document['id']}"
            )
            return

        document = get_document_by_id(raw_value, db)
        if not document:
            await update.message.reply_text("Документ с таким id не найден.")
            return

        set_selected_document_id(chat_id, raw_value)
        await update.message.reply_text(
            "Документ выбран.\n"
            f"Файл: {document['filename']}\n"
            f"id: {document['id']}"
        )
    finally:
        db.close()


async def selected_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        await update.message.reply_text("Не удалось определить чат.")
        return

    document_id = get_active_document_id(chat_id)
    if not document_id:
        await update.message.reply_text("Сейчас выбран режим поиска по всем документам.")
        return

    db = SessionLocal()
    try:
        document = get_document_by_id(document_id, db)
        if not document:
            clear_selected_document_id(chat_id)
            await update.message.reply_text("Ранее выбранный документ больше не найден. Поиск сброшен на все документы.")
            return

        await update.message.reply_text(
            "Текущий документ:\n"
            f"Файл: {document['filename']}\n"
            f"id: {document['id']}\n"
            f"status: {document['processing_status']}"
        )
    finally:
        db.close()


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /ask ваш вопрос")
        return

    question = " ".join(context.args).strip()
    chat_id = update.effective_chat.id if update.effective_chat else None
    db = SessionLocal()
    try:
        document_id = get_active_document_id(chat_id)
        if document_id:
            selected_document = get_document_by_id(document_id, db)
            if selected_document and selected_document["processing_status"] != "completed":
                await update.message.reply_text(
                    "Выбранный документ еще обрабатывается.\n"
                    f"Текущий статус: {selected_document['processing_status']}"
                )
                return

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


async def upload_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_document = update.message.document if update.message else None
    chat_id = update.effective_chat.id if update.effective_chat else None

    if not telegram_document or chat_id is None:
        await update.message.reply_text("Не удалось получить документ.")
        return

    db = SessionLocal()
    try:
        telegram_file = await context.bot.get_file(telegram_document.file_id)
        file_bytes = await telegram_file.download_as_bytearray()

        saved_document = await save_telegram_document(
            filename=telegram_document.file_name or "document",
            content_type=telegram_document.mime_type,
            content=bytes(file_bytes),
            db=db,
        )
        enqueue_document_processing(saved_document["id"])
        set_selected_document_id(chat_id, saved_document["id"])

        await update.message.reply_text(
            "Документ поставлен в очередь на обработку.\n"
            f"Файл: {saved_document['filename']}\n"
            f"id: {saved_document['id']}\n"
            "Этот документ выбран активным для следующих вопросов."
        )
    except Exception as exc:
        await update.message.reply_text(f"Ошибка загрузки документа: {exc}")
    finally:
        db.close()


async def fallback_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я понимаю команды:\n"
        "/documents\n"
        "/use <document_id|latest|all>\n"
        "/selected\n"
        "/ask <вопрос>\n"
        "Или отправьте PDF, TXT, MD файлом"
    )


def main():
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    ensure_runtime_schema()

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("documents", documents_command))
    app.add_handler(CommandHandler("use", use_command))
    app.add_handler(CommandHandler("selected", selected_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_document_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_message))

    print("Telegram bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
