"""CLI-точка входа для пакетной и одиночной обработки PDF-паспортов.

Скрипт позволяет запускать пайплайн из терминала и управлять ключевыми
параметрами через аргументы: пути директорий, выбор моделей и режим fallback.
"""

import argparse
from pathlib import Path

from core.document_pipeline import DocumentPipeline
from core.llm_extractor import LLMExtractor


def parse_args() -> argparse.Namespace:
    """Описывает и парсит аргументы командной строки.

    Returns:
        Объект `argparse.Namespace` с параметрами запуска пайплайна.
    """
    parser = argparse.ArgumentParser(description="Запуск обработки паспортов PDF")
    parser.add_argument("--input-dir", default="data/input", help="Папка со входными PDF")
    parser.add_argument("--processed-dir", default="data/processed", help="Папка для сегментов")
    parser.add_argument("--export-dir", default="data/export", help="Папка для JSON-выгрузки")
    parser.add_argument("--file", default=None, help="Обработать только один PDF-файл")
    parser.add_argument("--model", default="qwen2.5:3b-instruct", help="Текстовая LLM модель")
    parser.add_argument("--vision-model", default="llava:7b", help="Vision модель для fallback")
    parser.add_argument(
        "--use-vision-fallback",
        action="store_true",
        help="Включить fallback OCR через vision-модель",
    )
    return parser.parse_args()


if __name__ == "__main__":
    """Запускает пайплайн в режиме одного файла или batch-папки."""
    args = parse_args()

    extractor = LLMExtractor(
        model=args.model,
        vision_model=args.vision_model,
        use_vision_fallback=args.use_vision_fallback,
    )

    pipeline = DocumentPipeline(
        extractor=extractor,
        input_dir=args.input_dir,
        processed_dir=args.processed_dir,
        export_dir=args.export_dir,
    )

    if args.file:
        result = pipeline.process_file(Path(args.file))
        print("\nГотово. Обработан 1 файл.")
        print(f"JSON: {result['export_path']}")
    else:
        results = pipeline.process_input_dir()
        print(f"\nГотово. Обработано файлов: {len(results)}")
