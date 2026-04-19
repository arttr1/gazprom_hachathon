# Passport OCR System

Система для автоматической оцифровки паспортов промышленного оборудования (ТРЭИ, TECON, КЭАЗ и др.). Извлекает структурированные данные из PDF-документов с помощью OCR и локальных LLM-моделей.

## Демонстрационные материалы

- **Презентация**: `demonstrations/presentation.pptx` — презентация проекта с описанием архитектуры и возможностей системы.
- **Видео демострация**: `demonstrations/demo_video.mp4` — видеоролик с демонстрацией работы системы на примере реальных паспортов.

## Возможности

- Автоматическое определение типа страниц (текстовые PDF / сканы)
- OCR для сканированных документов (Tesseract или PaddleOCR)
- Извлечение таблиц из PDF
- LLM-структуризация данных через локальные модели (Ollama)
- Vision-fallback для улучшения качества распознавания проблемных сегментов
- Экспорт результатов в JSON и XLSX

---

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Или Python 3.11+ с Ollama локально (Ollama должен быть установлен и запущен для работы LLM-моделей)

### Запуск через Docker Compose (рекомендуется)

```bash
# Клонируйте репозиторий и перейдите в директорию проекта
cd /path/to/gazprom_hachathon

# Запустите все сервисы одной командой
docker-compose up --build
```

После запуска будут доступны:
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **Ollama**: http://localhost:11434

### Запуск вручную (без Docker)

> **Важно**: Для работы системы требуется установленный и запущенный Ollama с загруженными моделями. Без Ollama обработка документов не будет работать.

#### 1. Установка зависимостей

```bash
# Создайте виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или .venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt

# Установите системные зависимости (для OCR)
# Ubuntu/Debian:
sudo apt-get install poppler-utils tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng

# macOS:
brew install poppler tesseract tesseract-lang
```

#### 2. Установка и запуск Ollama

**Скачайте и установите Ollama с официального сайта: https://ollama.com/**

##### Установка на разных ОС:

**Windows:**
- Скачайте установщик с https://ollama.com/download
- Запустите установщик и следуйте инструкциям
- После установки Ollama будет доступен в командной строке

**macOS:**
```bash
# Через Homebrew (рекомендуется)
brew install ollama

# Или скачайте с сайта и установите вручную
```

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Linux (другие дистрибутивы):**
Скачайте подходящий пакет с https://ollama.com/download или используйте системный менеджер пакетов (например, для Arch: `pacman -S ollama`).

##### Запуск Ollama и скачивание моделей:

```bash
# Запустите Ollama сервер в фоне
ollama serve &

# Скачайте необходимые модели
ollama pull qwen2.5:3b-instruct
ollama pull llava:7b
```

#### 3. Запуск API-сервера

```bash
cd server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 4. Запуск фронтенда

```bash
cd frontend
npm install
npm run dev
```

---

## Использование

### Через веб-интерфейс

1. Откройте http://localhost:5173 в браузере
2. Перетащите PDF-файлы в область загрузки (до 10 файлов)
3. Нажмите "Обработать"
4. Скачайте результат в формате XLSX

### Через API

```bash
# Пример запроса через curl
curl -X POST http://localhost:8000/api/passports/extract \
  -F "files=@passport1.pdf" \
  -F "files=@passport2.pdf" \
  -o passports_export.xlsx
```

### Через CLI

```bash
# Обработка всех PDF в директории
python run_pipeline.py

# Обработка одного файла
python run_pipeline.py --file data/input/my_passport.pdf

# С указанием директорий
python run_pipeline.py \
  --input-dir data/input \
  --processed-dir data/processed \
  --export-dir data/export

# Включить vision-fallback для улучшения OCR
python run_pipeline.py --use-vision-fallback
```

---

## Структура проекта

```
gazprom_hachathon/
├── core/                    # Ядро обработки документов
│   ├── document_pipeline.py   # Оркестратор пайплайна
│   ├── pdf_processor.py       # Сегментация PDF и извлечение контента
│   ├── ocr_engine.py          # OCR-движок (Tesseract/PaddleOCR)
│   ├── llm_extractor.py       # LLM-извлечение структурированных данных
│   └── schemas.py             # Pydantic-схемы результата
├── server/                  # FastAPI-сервер
│   ├── app/
│   │   ├── api/routes.py          # API-эндпоинты
│   │   ├── config.py              # Конфигурация
│   │   └── services/
│   │       ├── passport_processing.py  # Обработка загрузок
│   │       └── xlsx_exporter.py        # Генерация XLSX
│   └── storage/               # Временное хранение файлов
├── frontend/                 # React-приложение
│   ├── src/
│   │   ├── features/file-upload/   # Компонент загрузки
│   │   └── app/                     # Основное приложение
│   └── nginx.conf              # Конфиг Nginx
├── demonstrations/            # Демонстрационные материалы
│   ├── presentation.pptx       # Презентация проекта
│   └── demo_video.mp4          # Видео демострация
├── data/                     # Данные для разработки
│   ├── input/                # Входные PDF
│   ├── processed/            # Сегменты и метаданные
│   └── export/               # JSON-результаты
├── tests/                    # Тесты
├── docker-compose.yml        # Оркестрация сервисов
├── run_pipeline.py           # CLI-точка входа
└── requirements.txt          # Python-зависимости
```

---

## Архитектура приложения

### Общая схема

```
PDF-файл
    │
    ▼
┌─────────────────────────────────────────────┐
│           PDFProcessor (core)               │
│  ┌─────────────────────────────────────────┐ │
│  │ 1. Определение типа страниц            │ │
│  │    (текстовая / скан)                  │ │
│  │ 2. Сегментация документа               │ │
│  │    - текстовые страницы → блоки        │ │
│  │    - сканированные → колонки + сегменты│ │
│  │ 3. OCR для сканов                      │ │
│  │ 4. Извлечение таблиц                   │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│         LLMExtractor (core)                 │
│  ┌─────────────────────────────────────────┐ │
│  │ 1. Сбор компактного контекста           │ │
│  │ 2. Vision-fallback (опционально)        │ │
│  │    для сегментов с низким confidence    │ │
│  │ 3. Извлечение структурированных данных  │ │
│  │    через LLM (Ollama)                   │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
    │
    ▼
PassportData (JSON) + XLSX-экспорт
```

---

## Модуль Core

Модуль `core/` содержит всю логику обработки документов. Это автономное ядро, которое может использоваться как через CLI, так и через API.

### core/document_pipeline.py

**Назначение**: Оркестратор обработки документов.

Класс `DocumentPipeline` управляет полным циклом обработки PDF:
1. Принимает входные PDF-файлы
2. Создает директории для результатов (`processed/`, `export/`)
3. Координирует обработку через `PDFProcessor` и `LLMExtractor`
4. Сохраняет сегменты изображений, метаданные и JSON-результаты

**Основные методы**:
- `process_input_dir()` — пакетная обработка всех PDF в директории
- `process_file()` — обработка одного файла

### core/pdf_processor.py

**Назначение**: Сегментация PDF и подготовка контекста для LLM.

Класс `PDFProcessor` выполняет первичную обработку PDF:
1. **Определение типа страницы**: текстовая (извлекается через MuPDF) или скан (требует OCR)
2. **Сегментация**:
   - Текстовые страницы разбиваются на блоки по вертикальным разрывам
   - Сканированные страницы сначала делятся на колонки (через анализ вертикальных проекций), затем каждая колонка сегментируется по горизонтальным промежуткам
3. **OCR**: для сканов запускается Tesseract или PaddleOCR
4. **Извлечение таблиц**: используется API MuPDF `find_tables()`
5. **Сбор контекста**: формируется компактный текстовый контекст для LLM

**Ключевые параметры**:
- `gap_threshold` — порог вертикального разрыва для текстовых страниц (по умолчанию 28.0)
- `min_gap_pixels` — минимальный размер промежутка для сегментации сканов (по умолчанию 45)
- `debug` — сохранение промежуточных изображений для отладки

### core/ocr_engine.py

**Назначение**: Унифицированный интерфейс OCR с оценкой качества.

Класс `OCREngine` предоставляет:
- Поддержку Tesseract и PaddleOCR (опционально)
- Предобработку изображений для улучшения качества OCR
- Возврат `confidence` — оценки качества распознавания (0-100)

Класс `OCRResult` — dataclass с полями:
- `text` — распознанный текст
- `confidence` — усредненная уверенность OCR
- `engine` — идентификатор движка (`tesseract` или `paddleocr`)

### core/llm_extractor.py

**Назначение**: Извлечение структурированных данных через LLM.

Класс `LLMExtractor` инкапсулирует работу с Ollama:

1. **Текстовая модель** (`qwen2.5:3b-instruct`):
   - Принимает компактный контекст из сегментов и таблиц
   - Возвращает структурированный JSON по схеме `PassportData`
   - Исправляет типичные OCR-ошибки (кириллица/латиница, перепутанные цифры)

2. **Vision-fallback** (`llava:7b`):
   - Активируется флагом `use_vision_fallback`
   - Обрабатывает только сегменты с низким confidence (< 62 по умолчанию)
   - Ограничено максимум 8 сегментами за запуск

3. **Основные методы**:
   - `extract_from_compact_context()` — основной метод для production
   - `enhance_low_confidence_segments()` — vision-fallback для проблемных сегментов
   - `build_compact_context()` — сбор контекста из сегментов и таблиц

### core/schemas.py

**Назначение**: Pydantic-модели для структурированного результата.

Основная модель `PassportData`:
```python
class PassportData(BaseModel):
    equipment_number: str          # Номер оборудования
    manufacturer: str              # Производитель (кратко)
    manufacturer_info: ManufacturerInfo  # Подробная информация о производителе
    model: str                     # Модель/наименование
    order_code: Optional[str]      # Код заказа
    serial_numbers: List[str]      # Заводские номера
    technical_specs: Dict[str, Any]  # Технические характеристики
    temperature_range: Optional[str]  # Температурный диапазон
    manufacture_date: Optional[date]  # Дата производства
    guarantee_months: Optional[int]   # Гарантия, мес.
    acceptance_date: Optional[date]    # Дата приемки
    otk_person: Optional[str]          # ОТК
    executive_system: Optional[str]    # Исполнительная система
    raw_text: Optional[str]           # Исходный текст для отладки
```

Модель также используется для генерации JSON Schema при вызове LLM с `format="json"`.

---

## API

### Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/health` | Проверка здоровья сервиса |
| POST | `/api/passports/extract` | Загрузка PDF и получение XLSX |

### Пример ответа XLSX

Генерируется Excel-файл с колонками:
- Файл
- Номер оборудования
- Производитель
- Бренд
- Предприятие
- Адрес
- Контакты
- Модель
- Код заказа
- Заводские номера
- Технические характеристики
- Температурный диапазон
- Дата производства
- Гарантия, мес.
- Дата приемки
- ОТК
- Исполнительная система

---

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `OLLAMA_HOST` | URL Ollama сервера | `http://localhost:11434` |

### Настройка моделей

В `run_pipeline.py` или при создании `LLMExtractor`:
```python
extractor = LLMExtractor(
    model="qwen2.5:3b-instruct",      # Текстовая модель
    vision_model="llava:7b",          # Vision-модель для fallback
    use_vision_fallback=False,        # Включить/выключить fallback
)
```

### OCR-движок

По умолчанию используется Tesseract. Для улучшенного распознавания русских сканов установите PaddleOCR:
```bash
pip install paddleocr
```

И включите в коде:
```python
processor = PDFProcessor(use_paddle_ocr=True)
```

---

## Разработка

### Структура данных

После обработки создается следующая структура:
```
data/processed/run_YYYYMMDD_HHMMSS/
├── prefix_timestamp/
│   ├── metadata.json        # Метаданные обработки
│   └── segments/            # Изображения сегментов
│       └── {prefix}_p{page}_s{num}.png
data/export/run_YYYYMMDD_HHMMSS/
└── prefix_timestamp.json    # Результат в JSON
```

### Тесты

```bash
# Запуск тестов
python -m pytest tests/

# Ручной запуск пайплайна для тестового PDF
python tests/test_llm.py
```

---

## Ограничения

- Максимум 10 PDF-файлов за один запрос
- Максимальный размер файла: 50 MB
- Требуется минимум 8GB RAM для LLM-моделей
- Время обработки зависит от размера документа и доступных ресурсов

---

## Технологический стек

- **OCR**: Tesseract, PaddleOCR (опционально)
- **PDF**: PyMuPDF (fitz), pdf2image
- **LLM**: Ollama (qwen2.5:3b-instruct, llava:7b)
- **API**: FastAPI + Uvicorn
- **Frontend**: React + TypeScript + Vite
- **Containerization**: Docker + Docker Compose
