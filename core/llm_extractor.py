"""Инструменты для извлечения структурированных данных из паспортов через LLM.

Модуль содержит класс `LLMExtractor`, который умеет:
1) принимать уже подготовленный контекст документа (текст и таблицы),
2) вызывать локальную текстовую модель для финальной структуризации в JSON,
3) при необходимости точечно улучшать слабые OCR-сегменты через vision-модель.

Основная идея: не отправлять все изображения в модель, а работать через компактный
контекст и включать визуальный fallback только там, где это действительно нужно.
"""

import ollama
from PIL import Image
import io
import time
from typing import List, Dict, Any
from .schemas import PassportData


class LLMExtractor:
    """Высокоуровневый адаптер для взаимодействия с локальными LLM-моделями.

    Класс инкапсулирует логику вызова Ollama для двух сценариев:
    - текстовая модель: принимает компактный контекст и возвращает `PassportData`;
    - vision-модель: используется только как fallback OCR для проблемных сегментов.
    """

    def __init__(
        self,
        model: str = "qwen2.5:3b-instruct",
        vision_model: str = "llava:7b",
        use_vision_fallback: bool = False,
    ):
        """Создает экземпляр экстрактора для локальных моделей.

        Args:
            model: Имя текстовой модели в Ollama для структуризации итогового JSON.
            vision_model: Имя vision-модели в Ollama для OCR fallback.
            use_vision_fallback: Включает точечную обработку слабых сегментов
                через vision-модель.
        """
        self.model = model
        self.vision_model = vision_model
        self.use_vision_fallback = use_vision_fallback
        self._vision_model_available = True
        print(
            f"LLMExtractor инициализирован: model={model}, "
            f"vision_fallback={'on' if use_vision_fallback else 'off'}"
        )

    def extract_from_segment(self, segment: Dict[str, Any]) -> PassportData:
        """Извлекает структурированные данные из одного image-сегмента.

        Метод нужен как совместимость со старым режимом, когда каждая картинка
        обрабатывалась отдельно. В текущем пайплайне чаще используется пакетный
        подход через `extract_from_compact_context`.

        Args:
            segment: Сегмент документа с изображением в `cropped_image` и служебными
                метаданными (страница, текст, bbox и т.д.).

        Returns:
            Заполненный объект `PassportData`.
        """
        image: Image.Image = segment["cropped_image"]

        # Конвертируем PIL → bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")

        img_bytes = img_bytes.getvalue()

        # Системный промпт (очень важный!)
        system_prompt = """Ты — эксперт по оцифровке паспортов промышленного оборудования (ТРЭИ, TECON, КЭАЗ и др.).
Извлеки ВСЮ полезную информацию из изображения паспорта.
Возвращай только валидный JSON по схеме PassportData.
ОБЯЗАТЕЛЬНО заполни поля equipment_number и manufacturer_info.
Если точные значения не найдены, укажи 'Не указано'."""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": "Извлеки все данные из этого паспорта оборудования.",
                        "images": [img_bytes]
                    }
                ],
                options={
                    "temperature": 0.0,
                    "num_ctx": 8192
                },
                format="json"          # важно для structured output
            )

            raw_json = response['message']['content']
            parsed = PassportData.model_validate_json(raw_json)

            # Добавляем сырой текст для отладки
            parsed.raw_text = segment.get("text", "")

            print(f"   Сегмент страницы {segment['page']} успешно обработан LLM")
            return parsed

        except Exception as e:
            print(f"   Ошибка LLM на странице {segment['page']}: {e}")
            # Возвращаем пустой объект, чтобы не падал весь пайплайн
            return PassportData(
                document_type="unknown",
                equipment_number="Не указано",
                manufacturer="Не распознано",
                manufacturer_info={
                    "name": "Не распознано",
                    "enterprise_name": "Не указано",
                    "address": "Не указано",
                    "contacts": "Не указано",
                },
                model="Не распознано",
                raw_text=segment.get("text", "")
            )

    def extract_from_compact_context(self, context: str) -> PassportData:
        """Извлекает паспортные данные из сжатого контекста документа.

        Args:
            context: Большой текст, собранный из OCR-сегментов и таблиц.

        Returns:
            Валидированный объект `PassportData`.

        Этот метод является основным для production-сценария, так как он значительно
        дешевле по ресурсам, чем обработка каждого изображения vision-моделью.
        """
        system_prompt = """Ты — эксперт по оцифровке паспортов промышленного оборудования.
Тебе передают уже извлеченный из PDF контент: текстовые сегменты и таблицы.
Сначала исправь типичные OCR-ошибки (кириллица/латиница, пропуски символов, перепутанные цифры).
Собери итоговую структурированную запись в JSON по схеме PassportData.
Поля equipment_number и manufacturer_info обязательны.
Если в документе нет точных данных — поставь 'Не указано' в строковые поля."""

        user_prompt = (
            "Ниже контент документа. Извлеки паспортные данные и верни только JSON.\n\n"
            f"{context}"
        )

        try:
            context_len = len(context or "")
            print(
                f"LLM compact-start: model={self.model}, context_chars={context_len}, num_ctx=8192"
            )
            started_at = time.perf_counter()
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": 0.0, "num_ctx": 8192},
                format=PassportData.model_json_schema(),
            )
            elapsed = time.perf_counter() - started_at
            print(f"LLM compact-done: elapsed={elapsed:.1f}s")
            raw_json = response["message"]["content"]
            return PassportData.model_validate_json(raw_json)
        except Exception as e:
            print(f"   Ошибка LLM (compact mode): {e}")
            return PassportData(
                document_type="unknown",
                equipment_number="Не указано",
                manufacturer="Не распознано",
                manufacturer_info={
                    "name": "Не распознано",
                    "enterprise_name": "Не указано",
                    "address": "Не указано",
                    "contacts": "Не указано",
                },
                model="Не распознано",
                raw_text=context[:3000] if context else None,
            )

    def enhance_low_confidence_segments(
        self,
        segments: List[Dict[str, Any]],
        confidence_threshold: float = 62.0,
        max_segments: int = 8,
    ) -> List[Dict[str, Any]]:
        """Улучшает сегменты с низким OCR-confidence через vision fallback.

        Алгоритм:
        1) определяет слабые сегменты по confidence и длине текста;
        2) отправляет только эти сегменты в vision-модель;
        3) подменяет текст, если результат объективно лучше исходного.

        Такой подход дает прирост качества без резкого роста времени/памяти.

        Args:
            segments: Список сегментов с OCR-текстом и confidence.
            confidence_threshold: Порог confidence, ниже которого сегмент считается
                кандидатом на fallback.
            max_segments: Максимальное число сегментов, которые можно отправить
                в vision-модель за один запуск.

        Returns:
            Обновленный список сегментов.
        """
        if not self.use_vision_fallback:
            print("VLM fallback отключен (use_vision_fallback=False)")
            return segments

        enhanced = []
        upgraded = 0
        total = len(segments)
        print(
            f"VLM fallback scan: total_segments={total}, threshold={confidence_threshold}, max={max_segments}"
        )
        for idx, seg in enumerate(segments, start=1):
            conf = float(seg.get("ocr_confidence", 0.0))
            text = (seg.get("text") or "").strip()
            needs_vlm = conf < confidence_threshold or len(text) < 20

            if needs_vlm and upgraded < max_segments and seg.get("cropped_image") is not None:
                print(
                    f"   [{idx}/{total}] fallback page={seg.get('page')} conf={conf:.1f} len={len(text)}"
                )
                vlm_text = self.extract_text_from_image_light(seg["cropped_image"])
                if vlm_text and len(vlm_text.strip()) > len(text):
                    seg["text"] = vlm_text.strip()
                    seg["ocr_engine"] = f"{seg.get('ocr_engine', 'ocr')}+vlm"
                    seg["ocr_confidence"] = max(conf, confidence_threshold + 5)
                    seg["vlm_fallback_used"] = True
                    upgraded += 1
            enhanced.append(seg)

        print(f"VLM fallback применен к {upgraded} сегментам")
        return enhanced

    def extract_text_from_image_light(self, image: Image.Image) -> str:
        """Распознает текст с изображения через легкую vision-модель.

        Метод вызывается только в fallback-сценарии для небольшого числа сегментов.
        Если vision-модель недоступна, метод возвращает пустую строку.

        Args:
            image: PIL-изображение проблемного сегмента.

        Returns:
            Распознанный текст или пустая строка, если распознавание не удалось.
        """
        if not self._vision_model_available:
            return ""

        img_bytes_io = io.BytesIO()
        image.save(img_bytes_io, format="PNG")
        img_bytes = img_bytes_io.getvalue()

        prompt = (
            "Это фрагмент скана технического паспорта оборудования. "
            "Извлеки только текст максимально точно. "
            "Сохрани исходный порядок строк, не добавляй комментарии."
        )

        try:
            started_at = time.perf_counter()
            response = ollama.chat(
                model=self.vision_model,
                messages=[{"role": "user", "content": prompt, "images": [img_bytes]}],
                options={"temperature": 0.0, "num_ctx": 4096},
            )
            elapsed = time.perf_counter() - started_at
            print(f"      VLM done: model={self.vision_model}, elapsed={elapsed:.1f}s")
            return (response.get("message", {}).get("content", "") or "").strip()
        except Exception as e:
            err = str(e)
            if "not found" in err.lower() or "404" in err:
                self._vision_model_available = False
                print(
                    f"   Vision-модель '{self.vision_model}' не найдена. "
                    "VLM fallback отключен до конца запуска."
                )
            else:
                print(f"   VLM OCR fallback не удался: {e}")
            return ""

    def build_compact_context(
        self,
        segments: List[Dict[str, Any]],
        tables: List[Dict[str, Any]] | None = None,
        max_chars: int = 14000,
    ) -> str:
        """Собирает компактный текстовый контекст из сегментов и таблиц.

        Контекст ограничивается по размеру, чтобы оставаться в пределах контекста
        локальной модели и не перегружать inference.

        Args:
            segments: Список текстовых/OCR сегментов документа.
            tables: Список таблиц, извлеченных из PDF.
            max_chars: Максимальный размер итогового контекста в символах.

        Returns:
            Строка контекста, готовая для передачи в LLM.
        """
        tables = tables or []
        parts: List[str] = []

        for idx, seg in enumerate(segments, start=1):
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            if len(text) > 1500:
                text = text[:1500] + " ..."
            parts.append(
                f"[SEGMENT {idx}] page={seg.get('page')} is_scan={seg.get('is_scan', False)}\n{text}"
            )

        for tbl in tables:
            rows = tbl.get("rows", [])[:12]
            row_lines = [" | ".join(map(str, row)) for row in rows]
            if row_lines:
                parts.append(
                    f"[TABLE] page={tbl.get('page')} index={tbl.get('table_index')}\n"
                    + "\n".join(row_lines)
                )

        context = "\n\n".join(parts)
        if len(context) > max_chars:
            context = context[:max_chars] + "\n\n[TRUNCATED]"
        return context

    def extract_from_all_segments(self, segments: List[Dict[str, Any]]) -> List[PassportData]:
        """Совместимый интерфейс для обработки списка сегментов.

        Метод оставлен для обратной совместимости с существующими тестами.
        Внутри он использует современный one-shot подход: собирает общий контекст
        и выполняет один вызов текстовой модели.

        Args:
            segments: Список сегментов документа.

        Returns:
            Список из одного элемента `PassportData` для совместимости старого API.
        """
        print("Собираю compact-context из сегментов...")
        context = self.build_compact_context(segments=segments, tables=None)
        data = self.extract_from_compact_context(context)
        data.raw_text = context[:5000]
        return [data]