"""Модуль сегментации PDF-документов и подготовки контекста для LLM.

Этот модуль отвечает за ранние этапы пайплайна:
- открытие PDF и определение типа страниц (текст/скан),
- сегментацию содержимого на логические фрагменты,
- OCR для сканированных сегментов,
- извлечение таблиц,
- сбор компактного текстового контекста для финальной структуризации в LLM.
"""

import os

import fitz
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
import pytesseract
from pathlib import Path
from typing import List, Dict, Any, Optional
from .ocr_engine import OCREngine

class PDFProcessor:
    """Процессор PDF, который превращает документ в набор пригодных для LLM данных.

    Экземпляр класса выполняет полный цикл подготовки данных:
    от сегментации и OCR до извлечения таблиц и сборки объединенного контекста.
    """

    def __init__(self, 
                 gap_threshold: float = 28.0,
                 min_gap_pixels: int = 45,
                 header_density_threshold: float = 0.25,
                 column_gap_threshold: int = 120,
                 debug: bool = False,
                 use_paddle_ocr: bool = False):
        """Инициализирует параметры сегментации и OCR.

        Параметры управляют чувствительностью разбиения колонок/абзацев и режимом
        отладки. В debug-режиме сохраняются служебные изображения, чтобы упростить
        проверку корректности работы алгоритмов.

        Args:
            gap_threshold: Минимальный вертикальный разрыв между блоками текста,
                при котором начинается новый сегмент на текстовой странице.
            min_gap_pixels: Минимальный размер пустого промежутка в пикселях для
                разбиения колонок скана на отдельные сегменты.
            header_density_threshold: Зарезервированный порог плотности для
                эвристик заголовков (параметр оставлен для настройки).
            column_gap_threshold: Зарезервированный порог для эвристик поиска
                межколоночных разрывов (параметр оставлен для настройки).
            debug: Включает сохранение промежуточных отладочных изображений.
            use_paddle_ocr: Если True и PaddleOCR доступен, OCR выполняется через
                PaddleOCR, иначе используется Tesseract.
        """
        self.gap_threshold = gap_threshold
        self.min_gap_pixels = min_gap_pixels
        self.header_density_threshold = header_density_threshold
        self.column_gap_threshold = column_gap_threshold
        self.debug = debug
        self.ocr_engine = OCREngine(use_paddle=use_paddle_ocr)
        self.debug_path = Path("data/debug_scan_segmentation")
        if self.debug:
            self.debug_path.mkdir(parents=True, exist_ok=True)

    def extract_segments(self, pdf_path: str | Path) -> List[Dict[str, Any]]:
        """Извлекает сегменты со всех страниц PDF и заполняет их текстом.

        Args:
            pdf_path: Путь к исходному PDF-документу.

        Returns:
            Список сегментов с изображением, текстом и метаданными.
        """
        pdf_path = Path(pdf_path)
        doc = fitz.open(pdf_path)
        page_images = convert_from_path(pdf_path, dpi=300)

        all_segments = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")
            has_text = bool(blocks) and any(b[4].strip() for b in blocks)

            pil_image = page_images[page_num]

            if has_text:
                print(f"Страница {page_num+1} — текстовая (MuPDF)")
                segments = self._process_text_page(page, blocks, page_num, pil_image)
            else:
                print(f"Страница {page_num+1} — скан")
                corrected_image = self._correct_orientation(pil_image, page_num)
                segments = self._process_scan_page(page_num, corrected_image)

            for seg in segments:
                seg["text"] = self._extract_segment_text(seg)
            all_segments.extend(segments)

        doc.close()
        return all_segments

    def extract_document_content(self, pdf_path: str | Path) -> Dict[str, Any]:
        """Запускает полный pre-LLM этап для одного PDF.

        Args:
            pdf_path: Путь к PDF, который нужно обработать.

        Returns:
            Словарь с тремя ключами:
        - `segments`: список сегментов с текстом и OCR-метаданными,
        - `tables`: извлеченные таблицы,
        - `context`: сжатый контекст, который можно напрямую отправлять в LLM.
        """
        pdf_path = Path(pdf_path)
        segments = self.extract_segments(pdf_path)
        tables = self.extract_tables(pdf_path)
        context = self.build_llm_context(segments=segments, tables=tables)
        return {
            "segments": segments,
            "tables": tables,
            "context": context,
        }


    def _correct_orientation(self, pil_image: Image.Image, page_num: int) -> Image.Image:
        """Пробует автоматически выровнять ориентацию сканированной страницы.

        Args:
            pil_image: Изображение страницы.
            page_num: Номер страницы (нумерация с нуля).

        Returns:
            Повернутое изображение или исходное, если поворот не определен.
        """
        try:
            osd = pytesseract.image_to_osd(
                pil_image,
                lang='eng',
                config='--psm 0 --oem 0'       
            )
            
            rotate_angle = int(osd.split("Rotate: ")[1].split("\n")[0])
            
            if rotate_angle != 0:
                print(f"Страница {page_num+1} повёрнута на {rotate_angle}° (Tesseract OSD)")
                corrected = pil_image.rotate(-rotate_angle, expand=True, resample=Image.BICUBIC)
                
                if self.debug:
                    corrected.save(self.debug_path / f"page{page_num+1}_after_rotation.png")
                return corrected
                
        except Exception as e:
            print(f"Tesseract OSD не сработал (страница {page_num+1}): {e}")
        
        return pil_image

    def _rotate_image(self, image: np.ndarray, angle: int) -> np.ndarray:
        """Поворачивает OpenCV-изображение на кратный 90 угол.

        Args:
            image: Изображение в формате NumPy/OpenCV.
            angle: Угол поворота, поддерживаются 90/180/270.

        Returns:
            Повернутое изображение.
        """
        if angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image


    def _process_text_page(self, page, blocks, page_num, pil_image):
        """Сегментирует текстовую страницу на блоки по вертикальным разрывам."""
        blocks.sort(key=lambda b: b[1])        
        segments = []
        current_segment = []
        last_y1 = None

        for block in blocks:
            x0, y0, x1, y1, text, *_ = block
            text = text.strip()
            if not text:
                continue

            if last_y1 is not None:
                gap = y0 - last_y1
                is_header = any(text.startswith(f"{i}.") for i in range(1, 11))
                if gap > self.gap_threshold or is_header:
                    if current_segment:
                        segments.append(self._build_segment(page, current_segment, page_num, pil_image))
                    current_segment = []

            current_segment.append(block)
            last_y1 = y1

        if current_segment:
            segments.append(self._build_segment(page, current_segment, page_num, pil_image))
        return segments

    def _process_scan_page(self, page_num: int, pil_image: Image.Image) -> List[Dict]:
        """Сегментирует скан: определяет колонки и делит каждую колонку на части.

        Args:
            page_num: Номер страницы (нумерация с нуля).
            pil_image: Изображение страницы.

        Returns:
            Список сегментов, полученных со сканированной страницы.
        """
        img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 15, 8)

        columns = self._detect_columns(binary, pil_image.width)
        segments = []

        for col_idx, (x_left, x_right) in enumerate(columns):
            column_img = pil_image.crop((x_left, 0, x_right, pil_image.height))
            column_binary = binary[:, x_left:x_right]
            col_segments = self._segment_column(column_img, column_binary, page_num, col_idx)
            segments.extend(col_segments)

        if self.debug:
            self._save_debug_columns(img, columns, page_num)

        return segments

    def _detect_columns(self, binary: np.ndarray, page_width: int) -> List[tuple]:
        """Определяет границы колонок на бинаризованной странице.

        Args:
            binary: Бинаризованная версия страницы (инвертированная маска текста).
            page_width: Ширина страницы в пикселях.

        Returns:
            Список диапазонов колонок в формате `(x_left, x_right)`.
        """

        height = binary.shape[0]
        crop_top = int(height * 0.12)
        crop_bot = int(height * 0.88)
        roi = binary[crop_top:crop_bot, :]

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

        cleaned = cv2.morphologyEx(roi, cv2.MORPH_OPEN, kernel, iterations=1)


        vertical_proj = np.sum(cleaned, axis=0) / 255.0

        vertical_proj = cv2.GaussianBlur(vertical_proj.reshape(1, -1), (1, 35), 0).flatten()

        min_gap_width = int(page_width * 0.015)           
        gap_threshold = int((crop_bot - crop_top) * 0.01) 
        min_column_width = int(page_width * 0.15)         

        gaps = []
        in_gap = False
        start = 0

        for x in range(1, page_width):
            if vertical_proj[x] < gap_threshold:
                if not in_gap:
                    in_gap = True
                    start = x
            else:
                if in_gap and (x - start) >= min_gap_width:
                    gaps.append((start, x))
                in_gap = False

        if in_gap and (page_width - start) >= min_gap_width:
            gaps.append((start, page_width))


        columns = []
        prev_mid = 0

        for gap_start, gap_end in gaps:
            gap_mid = (gap_start + gap_end) // 2
            

            if gap_mid - prev_mid >= min_column_width:
                columns.append((prev_mid, gap_mid))
            prev_mid = gap_mid


        if page_width - prev_mid >= min_column_width:
            columns.append((prev_mid, page_width))

        if not columns:
            columns = [(0, page_width)]

        print(f"Найдено {len(columns)} колонок: {[(left, right) for left, right in columns]}")
        return columns
    def _segment_column(self, column_img: Image.Image, column_binary: np.ndarray, page_num: int, col_idx: int) -> List[Dict]:
        """Разбивает одну колонку на сегменты по крупным горизонтальным промежуткам.

        Args:
            column_img: Изображение текущей колонки.
            column_binary: Бинарная матрица колонки.
            page_num: Номер страницы (нумерация с нуля).
            col_idx: Индекс колонки на странице.

        Returns:
            Список сегментов текущей колонки.
        """
        horizontal_proj = np.sum(column_binary, axis=1) / 255.0
        height = len(horizontal_proj)

        gaps = []
        in_gap = False
        start = 0
        for y in range(1, height):
            if horizontal_proj[y] < 8:
                if not in_gap:
                    in_gap = True
                    start = y
            else:
                if in_gap and (y - start) >= self.min_gap_pixels:
                    gaps.append((start, y))
                in_gap = False

        split_points = [0]
        for gs, ge in gaps:
            split_points.append((gs + ge) // 2)
        split_points.append(height)
        split_points = sorted(set(split_points))

        segments = []
        for i in range(len(split_points) - 1):
            y_start = split_points[i]
            y_end = split_points[i + 1]
            if y_end - y_start < 50:
                continue

            crop = column_img.crop((0, y_start, column_img.width, y_end))

            segments.append({
                "page": page_num + 1,
                "text": "",
                "bbox": (0, y_start, column_img.width, y_end),
                "cropped_image": crop,
                "is_header": False,
                "is_scan": True,
                "column": col_idx
            })
        return segments

    def _save_debug_columns(self, img: np.ndarray, columns: list, page_num: int):
        """Сохраняет отладочную картинку с границами найденных колонок.

        Args:
            img: Исходное изображение страницы.
            columns: Список границ колонок.
            page_num: Номер страницы (нумерация с нуля).
        """
        debug_img = img.copy()
        for x_left, x_right in columns:
            cv2.line(debug_img, (x_left, 0), (x_left, debug_img.shape[0]), (0, 255, 0), 4)
            cv2.line(debug_img, (x_right, 0), (x_right, debug_img.shape[0]), (0, 255, 0), 4)
        cv2.imwrite(str(self.debug_path / f"page{page_num+1}_debug_columns.png"), debug_img)

    def _build_segment(self, page, blocks, page_num, pil_image):
        """Создает единый объект сегмента для текстовых блоков MuPDF.

        Args:
            page: Объект страницы MuPDF.
            blocks: Список текстовых блоков страницы.
            page_num: Номер страницы (нумерация с нуля).
            pil_image: PIL-изображение страницы.

        Returns:
            Словарь сегмента в внутреннем формате пайплайна.
        """
        full_text = "\n".join(b[4].strip() for b in blocks if b[4].strip())
        x0 = min(b[0] for b in blocks)
        y0 = min(b[1] for b in blocks)
        x1 = max(b[2] for b in blocks)
        y1 = max(b[3] for b in blocks)
        cropped = pil_image.crop((x0, y0, x1, y1))

        return {
            "page": page_num + 1,
            "text": full_text,
            "bbox": (x0, y0, x1, y1),
            "cropped_image": cropped,
            "is_header": any(b[4].strip().startswith(("1.", "6.")) for b in blocks),
            "is_scan": False
        }

    def _extract_segment_text(self, segment: Dict[str, Any]) -> str:
        """Возвращает текст сегмента и обновляет OCR-метаданные.

        Args:
            segment: Сегмент документа, который нужно текстово заполнить.

        Returns:
            Нормализованный текст сегмента.

        Для текстовых PDF используется исходный текст MuPDF.
        Для сканов вызывается OCR-движок и записывается confidence/engine.
        """
        if segment.get("text", "").strip():
            segment["ocr_confidence"] = 100.0
            segment["ocr_engine"] = "mupdf"
            return segment["text"].strip()

        image = segment.get("cropped_image")
        if image is None:
            return ""

        try:
            ocr = self.ocr_engine.extract_text(image)
            segment["ocr_confidence"] = round(ocr.confidence, 2)
            segment["ocr_engine"] = ocr.engine
            return self._normalize_text(ocr.text)
        except Exception as e:
            print(f"OCR не удался для сегмента на стр. {segment.get('page')}: {e}")
            segment["ocr_confidence"] = 0.0
            segment["ocr_engine"] = "failed"
            return ""

    def _normalize_text(self, text: str) -> str:
        """Нормализует текст: удаляет пустые строки и лишние пробелы по краям.

        Args:
            text: Исходная текстовая строка.

        Returns:
            Нормализованный текст.
        """
        lines = [line.strip() for line in text.splitlines()]
        non_empty = [line for line in lines if line]
        return "\n".join(non_empty)

    def extract_tables(self, pdf_path: str | Path) -> List[Dict[str, Any]]:
        """Извлекает таблицы по всем страницам PDF, если движок их находит.

        Args:
            pdf_path: Путь к PDF-документу.

        Returns:
            Список таблиц по страницам.
        """
        pdf_path = Path(pdf_path)
        doc = fitz.open(pdf_path)
        all_tables: List[Dict[str, Any]] = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_tables = self._extract_tables_from_page(page, page_idx + 1)
            all_tables.extend(page_tables)

        doc.close()
        return all_tables

    def _extract_tables_from_page(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Пытается извлечь таблицы с одной страницы через API MuPDF.

        Args:
            page: Объект страницы MuPDF.
            page_num: Номер страницы (нумерация с единицы для пользователя).

        Returns:
            Список таблиц текущей страницы.
        """
        tables_result: List[Dict[str, Any]] = []
        try:
            finder = getattr(page, "find_tables", None)
            if finder is None:
                return tables_result

            found = finder()
            table_items = getattr(found, "tables", [])
            for idx, tbl in enumerate(table_items):
                rows = tbl.extract()
                cleaned_rows = self._clean_table_rows(rows)
                if not cleaned_rows:
                    continue
                tables_result.append(
                    {
                        "page": page_num,
                        "table_index": idx,
                        "rows": cleaned_rows,
                    }
                )
        except Exception as e:
            print(f"Ошибка извлечения таблиц на странице {page_num}: {e}")

        return tables_result

    def _clean_table_rows(self, rows: Optional[List[List[str]]]) -> List[List[str]]:
        """Очищает строки таблицы от пустых и нормализует содержимое ячеек.

        Args:
            rows: Таблица в виде списка строк и ячеек.

        Returns:
            Очищенные строки таблицы.
        """
        if not rows:
            return []
        cleaned: List[List[str]] = []
        for row in rows:
            if not row:
                continue
            normalized = [self._normalize_text(str(cell or "")) for cell in row]
            if any(cell for cell in normalized):
                cleaned.append(normalized)
        return cleaned

    def build_llm_context(
        self,
        segments: List[Dict[str, Any]],
        tables: Optional[List[Dict[str, Any]]] = None,
        max_chars: int = 14000,
    ) -> str:
        """
        Собирает сжатый контекст документа: только нужный текст + таблицы.
        Это снижает нагрузку на локальную LLM по сравнению с подачей изображений.

        Args:
            segments: Список сегментов с текстом.
            tables: Список таблиц.
            max_chars: Максимальная длина итогового контекста.

        Returns:
            Итоговый контекст в виде строки.
        """
        tables = tables or []
        parts: List[str] = []

        for i, seg in enumerate(segments, start=1):
            text = self._normalize_text(seg.get("text", ""))
            if not text:
                continue
            if len(text) > 1500:
                text = text[:1500] + " ..."
            parts.append(
                f"[SEGMENT {i}] page={seg.get('page')} is_scan={seg.get('is_scan', False)}\n{text}"
            )

        for table in tables:
            rows_preview = table["rows"][:12]
            rendered_rows = [" | ".join(row) for row in rows_preview]
            parts.append(
                f"[TABLE] page={table['page']} index={table['table_index']}\n"
                + "\n".join(rendered_rows)
            )

        context = "\n\n".join(parts)
        if len(context) > max_chars:
            context = context[:max_chars] + "\n\n[TRUNCATED]"
        return context