"""Локальный smoke-test полного OCR + LLM пайплайна для одного PDF."""

from core.pdf_processor import PDFProcessor
from core.llm_extractor import LLMExtractor
import time

pdf_file = "tests/2.pdf"          

processor = PDFProcessor(debug=True, use_paddle_ocr=False)
doc_content = processor.extract_document_content(pdf_file)
segments = doc_content["segments"]
tables = doc_content["tables"]

extractor = LLMExtractor(
    model="qwen2.5:3b-instruct",
    vision_model="llava:7b",
    use_vision_fallback=False,  # переключи в True при необходимости
)
segments = extractor.enhance_low_confidence_segments(
    segments,
    confidence_threshold=62.0,
    max_segments=8,
)
context = processor.build_llm_context(segments=segments, tables=tables)
print(f"Собран контекст для LLM: {len(context)} символов")

print("\nЗапуск LLM-извлечения...\n")
start = time.perf_counter()
passport = extractor.extract_from_compact_context(context)
elapsed = time.perf_counter() - start
passport.raw_text = context[:5000]

print(f"Найдено сегментов: {len(segments)}")
print(f"Найдено таблиц: {len(tables)}")
print(f"Время вызова LLM: {elapsed:.1f}s")
print(passport.model_dump_json(indent=2, ensure_ascii=False))