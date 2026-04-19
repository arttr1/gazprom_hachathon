# Passport OCR Server

FastAPI-сервер принимает PDF-паспорта, передает их в существующий пайплайн из `core`, собирает результат в XLSX и возвращает файл для скачивания.

## Архитектура

- `app/main.py` - создание FastAPI-приложения и CORS.
- `app/api/routes.py` - HTTP endpoints.
- `app/services/passport_processing.py` - сохранение PDF и запуск `core.document_pipeline.DocumentPipeline`.
- `app/services/xlsx_exporter.py` - генерация XLSX без дополнительных Excel-зависимостей.
- `storage/` - рабочие файлы сервера: uploads, processed, export.

## Запуск

### Docker Compose

Из корня проекта:

```bash
docker compose -f server/docker-compose.yml up --build
```

После запуска:

- frontend: `http://localhost:5173`
- server healthcheck: `http://localhost:8000/api/health`

Compose ожидает, что Ollama запущена на хосте и доступна по `http://host.docker.internal:11434`.

### Локально

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Для работы модели также нужен локальный Ollama и модели, которые использует `core`.

## API

- `GET /api/health` - проверка сервера.
- `POST /api/passports/extract` - multipart upload поля `files`, один или несколько PDF. Ответ: `passport_export.xlsx`.
