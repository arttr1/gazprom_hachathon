"""Оркестратор обработки документов от входного PDF до готового JSON.

Модуль предназначен для интерфейсного сценария, где пользователь может загрузить
один или несколько файлов. Для каждой сессии и для каждого документа создаются
отдельные каталоги, чтобы результаты никогда не смешивались между собой.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .llm_extractor import LLMExtractor
from .pdf_processor import PDFProcessor


def _slugify(value: str) -> str:
    """Преобразует произвольную строку в безопасный префикс для имени файла.

    Args:
        value: Исходная строка (например, имя PDF без расширения).

    Returns:
        Нормализованная строка из букв, цифр и символов `_`/`-`.
    """
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()
    return slug or "document"


class DocumentPipeline:
    """
    Пайплайн для single и batch обработки PDF:
    - входные файлы из data/input;
    - сегменты и метаданные в data/processed;
    - итоговые JSON в data/export.
    """

    def __init__(
        self,
        processor: PDFProcessor | None = None,
        extractor: LLMExtractor | None = None,
        input_dir: str | Path = "data/input",
        processed_dir: str | Path = "data/processed",
        export_dir: str | Path = "data/export",
    ):
        """Создает пайплайн и подготавливает рабочие каталоги проекта.

        Args:
            processor: Кастомный обработчик PDF, если нужно переопределить стандартный.
            extractor: Кастомный LLM-экстрактор.
            input_dir: Папка со входными PDF-файлами.
            processed_dir: Папка для сегментов и метаданных обработки.
            export_dir: Папка для итоговых JSON.
        """
        self.processor = processor or PDFProcessor(debug=True, use_paddle_ocr=False)
        self.extractor = extractor or LLMExtractor(
            model="qwen2.5:3b-instruct",
            vision_model="llava:7b",
            use_vision_fallback=False,
        )
        self.input_dir = Path(input_dir)
        self.processed_dir = Path(processed_dir)
        self.export_dir = Path(export_dir)

        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def process_input_dir(self) -> List[Dict[str, Any]]:
        """Обрабатывает все PDF в `input_dir` в рамках одного `run_*` каталога.

        Returns:
            Список словарей с путями к результатам по каждому файлу.
        """
        pdf_files = sorted(self.input_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"В {self.input_dir} нет PDF-файлов")
            return []

        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
        processed_run_dir = self.processed_dir / run_id
        export_run_dir = self.export_dir / run_id
        processed_run_dir.mkdir(parents=True, exist_ok=True)
        export_run_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for pdf_path in pdf_files:
            result = self.process_file(
                pdf_path=pdf_path,
                processed_run_dir=processed_run_dir,
                export_run_dir=export_run_dir,
            )
            results.append(result)
        return results

    def process_file(
        self,
        pdf_path: str | Path,
        processed_run_dir: str | Path | None = None,
        export_run_dir: str | Path | None = None,
    ) -> Dict[str, Any]:
        """Обрабатывает один PDF и сохраняет сегменты, метаданные и финальный JSON.

        Args:
            pdf_path: Путь к исходному PDF-файлу.
            processed_run_dir: Базовая папка для processed-данных текущего запуска.
            export_run_dir: Базовая папка для export-данных текущего запуска.

        Returns:
            Словарь с путями к основным артефактам обработки.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF не найден: {pdf_path}")

        doc_prefix = f"{_slugify(pdf_path.stem)}_{datetime.now().strftime('%H%M%S_%f')[:9]}"
        processed_base = Path(processed_run_dir) if processed_run_dir else self.processed_dir
        export_base = Path(export_run_dir) if export_run_dir else self.export_dir
        document_dir = processed_base / doc_prefix
        segments_dir = document_dir / "segments"
        document_dir.mkdir(parents=True, exist_ok=True)
        segments_dir.mkdir(parents=True, exist_ok=True)
        export_base.mkdir(parents=True, exist_ok=True)

        print(f"\nОбработка файла: {pdf_path.name}")
        content = self.processor.extract_document_content(pdf_path)
        segments = content["segments"]
        tables = content["tables"]

        segments = self.extractor.enhance_low_confidence_segments(
            segments,
            confidence_threshold=62.0,
            max_segments=8,
        )
        context = self.processor.build_llm_context(segments=segments, tables=tables)
        passport = self.extractor.extract_from_compact_context(context)
        passport.raw_text = context[:5000]

        self._save_segments(segments, segments_dir, doc_prefix)
        self._save_processed_metadata(document_dir / "metadata.json", pdf_path, segments, tables)

        export_path = export_base / f"{doc_prefix}.json"
        export_payload = passport.model_dump(mode="json")
        export_payload["source_file"] = pdf_path.name
        export_payload["processed_prefix"] = doc_prefix
        export_path.write_text(
            json.dumps(export_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"Сегменты: {segments_dir}")
        print(f"JSON: {export_path}")

        return {
            "source_file": str(pdf_path),
            "prefix": doc_prefix,
            "segments_dir": str(segments_dir),
            "metadata_path": str(document_dir / "metadata.json"),
            "export_path": str(export_path),
        }

    def _save_segments(self, segments: List[Dict[str, Any]], segments_dir: Path, prefix: str) -> None:
        """Сохраняет изображения сегментов в выделенную папку документа.

        Args:
            segments: Список сегментов с полем `cropped_image`.
            segments_dir: Целевая папка для PNG-файлов сегментов.
            prefix: Префикс, уникальный для текущего документа.
        """
        for idx, seg in enumerate(segments, start=1):
            image = seg.get("cropped_image")
            if image is None:
                continue
            page = seg.get("page", 0)
            filename = f"{prefix}_p{page:02d}_s{idx:03d}.png"
            image.save(segments_dir / filename, format="PNG")

    def _save_processed_metadata(
        self,
        output_path: Path,
        source_pdf: Path,
        segments: List[Dict[str, Any]],
        tables: List[Dict[str, Any]],
    ) -> None:
        """Сохраняет сериализованные метаданные обработки в `metadata.json`.

        Args:
            output_path: Путь к выходному JSON с метаданными.
            source_pdf: Исходный PDF-файл.
            segments: Список сегментов после OCR/fallback.
            tables: Список извлеченных таблиц.
        """
        serializable_segments: List[Dict[str, Any]] = []
        for seg in segments:
            serializable_segments.append(
                {
                    "page": seg.get("page"),
                    "bbox": seg.get("bbox"),
                    "is_scan": seg.get("is_scan"),
                    "is_header": seg.get("is_header"),
                    "column": seg.get("column"),
                    "text": seg.get("text"),
                    "ocr_confidence": seg.get("ocr_confidence"),
                    "ocr_engine": seg.get("ocr_engine"),
                    "vlm_fallback_used": seg.get("vlm_fallback_used", False),
                }
            )

        payload = {
            "source_file": source_pdf.name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "segments_count": len(serializable_segments),
            "tables_count": len(tables),
            "segments": serializable_segments,
            "tables": tables,
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
