import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from ..config import EXPORT_DIR, PROCESSED_DIR, PROJECT_ROOT, UPLOADS_DIR

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class PassportProcessingError(Exception):
    """Raised when uploaded documents cannot be processed."""


class PassportProcessingService:
    max_file_size = 50 * 1024 * 1024

    def __init__(self) -> None:
        self._pipeline: Any | None = None

    async def process_uploads(self, files: list[UploadFile]) -> list[dict]:
        if len(files) > 10:
            raise PassportProcessingError("За один раз можно обработать не больше 10 PDF-файлов")

        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S_") + uuid4().hex[:8]
        upload_dir = UPLOADS_DIR / run_id
        processed_run_dir = PROCESSED_DIR / run_id
        export_run_dir = EXPORT_DIR / run_id

        upload_dir.mkdir(parents=True, exist_ok=True)
        processed_run_dir.mkdir(parents=True, exist_ok=True)
        export_run_dir.mkdir(parents=True, exist_ok=True)

        pdf_paths = []
        for file in files:
            pdf_paths.append(await self._save_pdf(file, upload_dir))

        try:
            return await asyncio.to_thread(
                self._process_saved_files,
                pdf_paths,
                processed_run_dir,
                export_run_dir,
            )
        except PassportProcessingError:
            raise
        except ModuleNotFoundError as exc:
            raise PassportProcessingError(
                f"Не установлена зависимость для обработки PDF: {exc.name}"
            ) from exc
        except ConnectionError as exc:
            raise PassportProcessingError(
                "Не удалось подключиться к локальной модели. Проверьте Ollama и доступность модели."
            ) from exc
        except Exception as exc:
            message = str(exc)
            if "ollama" in message.lower() or "connection refused" in message.lower():
                raise PassportProcessingError(
                    "Не удалось подключиться к Ollama. Запустите Ollama и проверьте модель."
                ) from exc
            raise PassportProcessingError(f"Ошибка пайплайна обработки: {message}") from exc

    async def _save_pdf(self, file: UploadFile, upload_dir: Path) -> Path:
        filename = Path(file.filename or "").name
        if not filename:
            raise PassportProcessingError("Файл без имени не может быть обработан")

        if not self._is_pdf(file, filename):
            raise PassportProcessingError(f"Поддерживается только PDF: {filename}")

        target_path = upload_dir / f"{uuid4().hex}_{filename}"
        total_size = 0
        with target_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > self.max_file_size:
                    target_path.unlink(missing_ok=True)
                    raise PassportProcessingError(f"Файл слишком большой: {filename}")
                target.write(chunk)

        if total_size == 0:
            target_path.unlink(missing_ok=True)
            raise PassportProcessingError(f"Файл пустой: {filename}")

        return target_path

    def _process_saved_files(
        self,
        pdf_paths: list[Path],
        processed_run_dir: Path,
        export_run_dir: Path,
    ) -> list[dict]:
        passports = []

        for pdf_path in pdf_paths:
            result = self._get_pipeline().process_file(
                pdf_path=pdf_path,
                processed_run_dir=processed_run_dir,
                export_run_dir=export_run_dir,
            )
            export_path = Path(result["export_path"])
            if not export_path.exists():
                raise PassportProcessingError(f"Пайплайн не создал JSON для файла {pdf_path.name}")
            passports.append(json.loads(export_path.read_text(encoding="utf-8")))

        if not passports:
            raise PassportProcessingError("Не удалось получить данные из PDF")

        return passports

    def _is_pdf(self, file: UploadFile, filename: str) -> bool:
        content_type = (file.content_type or "").lower()
        return content_type == "application/pdf" or filename.lower().endswith(".pdf")

    def _get_pipeline(self) -> Any:
        if self._pipeline is None:
            from core.document_pipeline import DocumentPipeline

            self._pipeline = DocumentPipeline(
                input_dir=UPLOADS_DIR,
                processed_dir=PROCESSED_DIR,
                export_dir=EXPORT_DIR,
            )

        return self._pipeline
