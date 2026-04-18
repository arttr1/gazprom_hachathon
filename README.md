# Passport OCR Pipeline (for UI Developer)

Этот проект обрабатывает сканы PDF-паспортов оборудования и сохраняет результат в структурированный JSON.
Документ ориентирован на разработчика интерфейса: куда класть загруженные пользователем файлы, где читать готовые результаты и как запускать обработку.

## Что делает пайплайн

1. Берет PDF-файлы из входной папки.
2. Сегментирует страницы (включая сканы и колонки).
3. Выполняет OCR по сегментам.
4. Собирает текстовый контекст + таблицы.
5. Вызывает локальную LLM для структуризации в `PassportData`.
6. Сохраняет:
   - сегменты и метаданные обработки,
   - итоговый JSON для каждого документа.

## Папки данных (важно для интерфейса)

- Входные файлы от пользователя: `data/input`
- Промежуточные артефакты (сегменты, метаданные): `data/processed`
- Готовые JSON для UI/интеграции: `data/export`

### Рекомендуемый flow в интерфейсе

1. Пользователь загружает 1 или N PDF.
2. UI сохраняет их в `data/input`.
3. UI запускает `run_pipeline.py`.
4. UI читает результаты из `data/export/<run_id>/`.

## Структура результатов

При пакетной обработке создается отдельная папка запуска:

- `data/processed/run_YYYYMMDD_HHMMSS/`
- `data/export/run_YYYYMMDD_HHMMSS/`

Для каждого входного PDF создается уникальный префикс:

- `some_file_153245_123`

Пример структуры:

```text
data/
  input/
    1.pdf
    2.pdf
  processed/
    run_20260418_143652/
      1_143652_99/
        segments/
          1_143652_99_p01_s001.png
          ...
        metadata.json
      2_143715_74/
        segments/
          ...
        metadata.json
  export/
    run_20260418_143652/
      1_143652_99.json
      2_143715_74.json
```

Это гарантирует, что данные разных документов и разных запусков не смешиваются.

## Как запускать

### Batch (все PDF из `data/input`)

```bash
python run_pipeline.py
```

### Один файл

```bash
python run_pipeline.py --file tests/1.pdf
```

### Включить vision fallback (тяжелее по ресурсам)

```bash
python run_pipeline.py --use-vision-fallback
```

## Полезные CLI-параметры

- `--input-dir` (по умолчанию `data/input`)
- `--processed-dir` (по умолчанию `data/processed`)
- `--export-dir` (по умолчанию `data/export`)
- `--file` (обработка только одного PDF)
- `--model` (текстовая LLM, по умолчанию `qwen2.5:3b-instruct`)
- `--vision-model` (по умолчанию `llava:7b`)
- `--use-vision-fallback` (выключен по умолчанию)

## Формат итогового JSON

Каждый файл в `data/export/<run_id>/*.json` содержит структуру `PassportData` + служебные поля:

- `source_file` — имя исходного PDF
- `processed_prefix` — префикс документа в текущем запуске

Ключевые поля `PassportData`:

- `equipment_number`
- `manufacturer`
- `manufacturer_info`:
  - `name`
  - `enterprise_name`
  - `address`
  - `contacts`
- `model`
- `serial_numbers`
- `technical_specs`
- и др. поля паспорта

## Интеграционные рекомендации для UI

- После загрузки файлов показывать пользователю `run_id` текущей обработки.
- Для списка результатов читать `data/export/<run_id>/*.json`.
- Для "показать источник" использовать:
  - `data/processed/<run_id>/<prefix>/segments/*.png`
  - `data/processed/<run_id>/<prefix>/metadata.json`
- Не писать пользовательские файлы сразу в `processed`/`export`; только в `input`.

## Зависимости и локальные модели

Минимально нужно:

- Python-зависимости из `requirements.txt`
- Ollama с моделями:
  - `qwen2.5:3b-instruct`
  - `llava:7b` (только если используете vision fallback)

Пример:

```bash
ollama pull qwen2.5:3b-instruct
ollama pull llava:7b
```

