"""Локальный тест сегментации PDF без LLM.

Скрипт нужен для ручной проверки качества разбиения страницы на сегменты и
сохранения соответствующих изображений в debug-папку.
"""

from core.pdf_processor import PDFProcessor
from pathlib import Path
from PIL import Image
import sys


def test_full_pipeline(pdf_path: str, debug: bool = True):
    """
    Полный тест: 
    1. Автоматический поворот страницы (если нужно)
    2. Сегментация (текст / скан / колонки)
    3. Сохранение всех сегментов + debug-изображений
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        print(f"Файл не найден: {pdf_path}")
        return

    debug_folder = Path("data/debug_segments")
    debug_folder.mkdir(parents=True, exist_ok=True)

    processor = PDFProcessor(
        gap_threshold=28.0,
        min_gap_pixels=20,           # уменьшил, чтобы лучше ловить пробелы между абзацами
        header_density_threshold=0.22,
        column_gap_threshold=80,     # ← теперь используем новый параметр
        debug=True
    )

    print(f"Запуск полного теста: {pdf_path.name}")
    print(f"Результаты: {debug_folder.absolute()}\n")

    segments = processor.extract_segments(pdf_path)

    print(f"Обработано страниц: {len(set(s['page'] for s in segments))}")
    print(f"Найдено сегментов всего: {len(segments)}\n")
    print(f"{'№':<3} {'Стр.':<5} {'Тип':<8} {'Колонка':<8} {'Размер':<18} {'Заголовок?'}   Имя файла")
    print("-" * 95)

    for i, seg in enumerate(segments):
        page = seg["page"]
        is_scan = seg.get("is_scan", False)
        col = seg.get("column", 0)
        size = f"{seg['cropped_image'].width}×{seg['cropped_image'].height}"
        is_header = "Да" if seg.get("is_header") else "Нет"
        seg_type = "СКАН" if is_scan else "Текст"

        if is_scan:
            filename = f"page{page}_SCAN_col{col}_seg{i+1:02d}.png"
        else:
            filename = f"page{page}_seg{i+1:02d}.png"

        save_path = debug_folder / filename
        seg["cropped_image"].save(save_path, format="PNG", quality=95)

        print(f"{i+1:<3} {page:<5} {seg_type:<8} {col:<8} {size:<18} {is_header:<9} {filename}")

    print("\nТест завершен.")
    print("   • Все сегменты сохранены в data/debug_segments/")
    if debug:
        print("   • В папке data/debug_scan_segmentation лежат:")
        print("       - изображения с зелёными линиями (колонки и пробелы)")
        print("       - исправленные после поворота страницы (_after_rotation.png)")

    if segments:
        print("\nПоказываю первое и последнее изображение сегмента...")
        segments[0]["cropped_image"].show(title=f"Первый сегмент (страница {segments[0]['page']})")
        segments[-1]["cropped_image"].show(title=f"Последний сегмент (страница {segments[-1]['page']})")



if __name__ == "__main__":
    
    pdf_file = "tests/3.pdf"   

    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]

    test_full_pipeline(pdf_file, debug=True)