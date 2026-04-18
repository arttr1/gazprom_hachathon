"""OCR-слой проекта: распознавание текста и оценка качества распознавания.

Модуль предоставляет унифицированный интерфейс к OCR-движкам и возвращает
не только текст, но и confidence, чтобы можно было принимать решения о
дополнительной обработке (например, запускать fallback через vision-модель).
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image


@dataclass
class OCRResult:
    """Результат OCR для одного изображения.

    Args:
        text: Распознанный текст.
        confidence: Усредненная уверенность OCR в диапазоне 0..100.
        engine: Идентификатор движка, который выполнил распознавание.
    """

    text: str
    confidence: float
    engine: str


class OCREngine:
    """
    OCR-движок с confidence:
    - по умолчанию Tesseract;
    - при наличии paddleocr можно включить use_paddle=True.
    """

    def __init__(self, use_paddle: bool = False):
        """Инициализирует OCR-движок и опционально включает PaddleOCR.

        Args:
            use_paddle: Если True, движок попытается использовать PaddleOCR;
                при недоступности автоматически переключится на Tesseract.
        """
        self.use_paddle = use_paddle
        self._paddle = None

        if use_paddle:
            try:
                from paddleocr import PaddleOCR  # type: ignore

                self._paddle = PaddleOCR(lang="ru", use_angle_cls=True, show_log=False)
                print("OCR: использую PaddleOCR")
            except Exception as exc:
                print(f"OCR: PaddleOCR недоступен, fallback на Tesseract ({exc})")
                self.use_paddle = False

    def extract_text(self, image: Image.Image) -> OCRResult:
        """Запускает OCR через выбранный движок и возвращает `OCRResult`.

        Args:
            image: Изображение сегмента в формате PIL.

        Returns:
            Объект `OCRResult` с текстом, confidence и именем движка.
        """
        if self.use_paddle and self._paddle is not None:
            return self._extract_text_paddle(image)
        return self._extract_text_tesseract(image)

    def _extract_text_tesseract(self, image: Image.Image) -> OCRResult:
        """Распознает текст через Tesseract и усредняет confidence по токенам.

        Args:
            image: Изображение сегмента.

        Returns:
            Результат OCR через Tesseract.
        """
        prep = self._preprocess(image)
        data = pytesseract.image_to_data(
            prep,
            lang="rus+eng",
            config="--oem 1 --psm 6",
            output_type=pytesseract.Output.DICT,
        )

        words = []
        confidences = []
        n = len(data.get("text", []))
        for i in range(n):
            token = (data["text"][i] or "").strip()
            if not token:
                continue
            conf_raw = str(data["conf"][i]).strip()
            try:
                conf = float(conf_raw)
            except ValueError:
                conf = -1.0
            words.append(token)
            if conf >= 0:
                confidences.append(conf)

        text = " ".join(words).strip()
        confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
        return OCRResult(text=text, confidence=confidence, engine="tesseract")

    def _extract_text_paddle(self, image: Image.Image) -> OCRResult:
        """Распознает текст через PaddleOCR и рассчитывает итоговый confidence.

        Args:
            image: Изображение сегмента.

        Returns:
            Результат OCR через PaddleOCR.
        """
        arr = np.array(image.convert("RGB"))
        result = self._paddle.ocr(arr, cls=True)  # type: ignore[union-attr]
        if not result or not result[0]:
            return OCRResult(text="", confidence=0.0, engine="paddleocr")

        lines = []
        confidences = []
        for item in result[0]:
            if not item or len(item) < 2:
                continue
            text = (item[1][0] or "").strip()
            conf = float(item[1][1]) * 100.0
            if text:
                lines.append(text)
                confidences.append(conf)

        full_text = "\n".join(lines)
        confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
        return OCRResult(text=full_text, confidence=confidence, engine="paddleocr")

    def _preprocess(self, image: Image.Image) -> Image.Image:
        """Легкий препроцессинг для повышения качества OCR.

        Args:
            image: Исходное изображение сегмента.

        Returns:
            Подготовленное бинаризованное изображение.
        """
        gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        return Image.fromarray(binary)
