# AIKnowledgeAssistant

Backend-платформа AI Knowledge Assistant на Python, FastAPI, SQLAlchemy и Pydantic: загрузка и обработка документов, извлечение текста, чанкинг, embeddings, кеширование ответов и RAG-пайплайн для вопросов по пользовательским файлам с дальнейшей интеграцией Telegram.

Основной сценарий:

1. Пользователь отправляет файл в Telegram.
2. Поддерживаемые форматы:
   - `PDF`
   - `Markdown`
   - `TXT`
3. Пользователь пишет вопрос, например:
   - `Что в этом документе?`
4. Бот анализирует содержимое документа и отвечает, например:
   - `В документе указано...`

## Цель проекта

Сделать систему, которая:

- принимает документ от пользователя;
- извлекает из него текст;
- передает текст в RAG-слой;
- отвечает на вопросы по содержимому документа;
- в дальнейшем интегрируется с Telegram-ботом.

На текущем этапе цель реализована частично: подготовлен backend-каркас, добавлены API для загрузки документа, получения списка документов, одного документа и просмотра чанков, а также базовый RAG-поток с embeddings, кешированием и LLM generation, но решение еще не доведено до production-ready состояния.
Приложение уже сохраняет загруженные файлы на диск, извлекает текст из `PDF`, `TXT` и `Markdown`, разбивает текст на чанки, строит embedding-вектора, сохраняет документы и чанки в `PostgreSQL`, а также использует найденные фрагменты для генерации ответа.

## Что есть на текущем этапе

В проекте уже сделано:

- создано приложение `FastAPI`;
- подключен роутер с префиксом `/api`;
- есть endpoint `GET /api/health`;
- есть endpoint `POST /api/ask`;
- есть endpoint `POST /api/upload`;
- есть endpoint `GET /api/documents`;
- есть endpoint `GET /api/documents/{document_id}`;
- есть endpoint `GET /api/documents/{document_id}/chunks`;
- логика ответа вынесена в отдельный сервис `rag_service`;
- логика загрузки документа вынесена в отдельный сервис `document_service`;
- логика разбиения текста на чанки вынесена в отдельный сервис `chunk_service`;
- логика построения embeddings вынесена в отдельный сервис `embedding_service`;
- логика генерации ответа через LLM вынесена в отдельный сервис `llm_service`;
- логика векторного поиска вынесена в отдельный сервис `vector_store_service`;
- логика rerank найденных чанков вынесена в отдельный сервис `rerank_service`;
- добавлен Telegram-бот для запроса последних документов и вопросов по базе;
- логика кеширования ответов вынесена в отдельный сервис `cache_service`;
- добавлены Pydantic-схемы для запроса, ответа, документа и чанков;
- добавлен конфиг через `pydantic-settings`;
- добавлено подключение к `PostgreSQL` через `SQLAlchemy`;
- добавлены ORM-модели `Document` и `Chunk`;
- добавлено кеширование ответов через `Redis`;
- добавлено внешнее векторное хранилище `Qdrant`;
- добавлена директория загрузки файлов `data/uploads`;
- добавлено извлечение текста из `PDF`, `TXT` и `MD`;
- добавлено разбиение извлеченного текста на чанки с `chunk_size` и `overlap`;
- добавлено построение embeddings для чанков документа;
- добавлен поиск похожих чанков через `Qdrant`;
- добавлен LLM-rerank для повторной сортировки найденных чанков;
- добавлена генерация ответа через OpenAI API на основе найденного контекста;
- добавлены `Dockerfile`, `docker-compose.yml` и `requirements.txt` для контейнерного запуска;
- добавлен отдельный `bot`-сервис в `docker-compose.yml`;
- в ответе по документу появились `stored_path`, `text_length` и `preview`.

Как это работает сейчас:

- `app/main.py` создает объект `FastAPI` и подключает роуты с общим префиксом `/api`;
- `app/api/routes.py` принимает HTTP-запросы и передает работу в сервисы;
- `app/schemas/query.py` описывает структуру запроса на `/api/ask` и структуру ответа;
- `app/schemas/document.py` описывает структуру ответа при загрузке документа и списка документов;
- `app/schemas/chunk.py` описывает структуру ответа для чанков документа;
- `app/services/document_service.py` валидирует загружаемый файл, создает директорию загрузки, сохраняет файл на диск, извлекает текст, разбивает его на чанки, строит embeddings, сохраняет документ и чанки в базу данных и возвращает метаданные;
- `app/services/chunk_service.py` отвечает за разбиение текста на чанки, построение embeddings для чанков, similarity search и выдачу чанков по `document_id`;
- `app/services/embedding_service.py` вызывает OpenAI Embeddings API для построения векторных представлений текста;
- `app/services/llm_service.py` формирует ответ через OpenAI Responses API на основе найденных чанков;
- `app/services/vector_store_service.py` отвечает за создание коллекции в `Qdrant`, загрузку чанков и поиск по embedding-векторам;
- `app/services/rerank_service.py` выполняет rerank найденных чанков перед генерацией ответа;
- `app/services/cache_service.py` работает с `Redis` и кеширует ответы на вопросы;
- `app/services/rag_service.py` строит embedding для вопроса, ищет похожие чанки в `Qdrant`, применяет rerank, использует кеш и генерирует ответ на основе найденного контекста;
- `app/db/database.py` создает `SQLAlchemy` engine, `SessionLocal` и dependency `get_db`;
- `app/db/models.py` описывает таблицы документов и чанков;
- `app/core/config.py` теперь содержит настройку `upload_dir`, OpenAI-настройки, а также параметры `PostgreSQL`, `Redis`, `Qdrant` и Telegram-бота;
- `app/bot.py` запускает Telegram-бота с командами `/start`, `/documents` и `/ask`.

Что реально происходит при вызове endpoint:

- `GET /api/health` возвращает `{"status": "ok"}`;
- `POST /api/upload` принимает файл, проверяет имя, тип или расширение, сохраняет его в каталог `data/uploads`, извлекает текст, разбивает его на чанки, строит embeddings, сохраняет документ и чанки в `PostgreSQL`, загружает векторы в `Qdrant` и возвращает метаданные документа;
- `GET /api/documents` возвращает список загруженных документов из базы данных вместе с путем хранения, длиной извлеченного текста и кратким превью;
- `GET /api/documents/{document_id}` возвращает один документ по `id`;
- `GET /api/documents/{document_id}/chunks` возвращает список чанков, связанных с выбранным документом, из базы данных;
- `POST /api/ask` принимает вопрос и необязательный `document_id`, сначала проверяет кеш в `Redis`, затем при необходимости строит embedding вопроса, ищет похожие чанки в `Qdrant`, применяет rerank и генерирует ответ через LLM.

Что еще не реализовано:

- более надежная обработка ошибок OpenAI API и retry-логика;
- production-ready асинхронная обработка embeddings и очередей задач;
- более гибкий выбор документа в Telegram-боте без фиксированного `TELEGRAM_DEFAULT_DOCUMENT_ID`.

Текущее состояние:

- загруженные файлы сохраняются в `data/uploads`, а документы и чанки теперь сохраняются в `PostgreSQL`;
- текст документа извлекается, разбивается на чанки, обогащается embeddings и индексируется в `Qdrant`;
- endpoint `/api/ask` использует retrieval через `Qdrant`, кеширование в `Redis`, LLM-rerank и LLM generation;
- в проект добавлен Telegram-бот для просмотра последних документов и запросов к RAG-пайплайну;
- текущая реализация подходит как учебный и архитектурный старт, но еще не решает основную задачу проекта.

Для запуска текущей версии нужны зависимости:

```bash
pip install -r requirements.txt
```

Примеры запуска и проверки:

```bash
uvicorn app.main:app --reload
```

```bash
curl http://127.0.0.1:8000/api/health
```

```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?"}'
```

```bash
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "file=@example.txt"
```

```bash
curl http://127.0.0.1:8000/api/documents
```

```bash
curl http://127.0.0.1:8000/api/documents/<document_id>
```

```bash
curl http://127.0.0.1:8000/api/documents/<document_id>/chunks
```

```bash
docker compose up --build
```

## Текущая структура проекта

```text
AIKnowledgeAssistant/
├── app/
│   ├── api/
│   │   └── routes.py
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   ├── database.py
│   │   └── models.py
│   ├── schemas/
│   │   ├── document.py
│   │   ├── chunk.py
│   │   └── query.py
│   ├── services/
│   │   ├── cache_service.py
│   │   ├── chunk_service.py
│   │   ├── document_service.py
│   │   ├── document_query_service.py
│   │   ├── embedding_service.py
│   │   ├── llm_service.py
│   │   ├── rag_service.py
│   │   ├── rerank_service.py
│   │   └── vector_store_service.py
│   ├── bot.py
│   └── main.py
├── data/
│   └── uploads/
├── Dockerfile
├── docker-compose.yml
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

Структура разделена по ролям:

- `api` - маршруты и HTTP-слой;
- `schemas` - входные и выходные модели данных;
- `services` - бизнес-логика, retrieval, embeddings, кеширование и answer generation;
- `db` - подключение к базе данных и ORM-модели документов и чанков;
- `core` - конфигурация приложения;
- `data/uploads` - каталог, в который сохраняются загруженные файлы.
