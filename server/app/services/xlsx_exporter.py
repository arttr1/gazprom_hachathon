import io
import json
import re
import zipfile
from datetime import date, datetime
from typing import Any
from xml.sax.saxutils import escape


HEADERS = [
    ("source_file", "Файл"),
    ("equipment_number", "Номер оборудования"),
    ("manufacturer", "Производитель"),
    ("manufacturer_name", "Бренд"),
    ("manufacturer_enterprise_name", "Предприятие"),
    ("manufacturer_address", "Адрес"),
    ("manufacturer_contacts", "Контакты"),
    ("model", "Модель"),
    ("order_code", "Код заказа"),
    ("serial_numbers", "Заводские номера"),
    ("technical_specs", "Технические характеристики"),
    ("temperature_range", "Температурный диапазон"),
    ("manufacture_date", "Дата производства"),
    ("guarantee_months", "Гарантия, мес."),
    ("acceptance_date", "Дата приемки"),
    ("otk_person", "ОТК"),
    ("executive_system", "Исполнительная система"),
    ("processed_prefix", "Префикс обработки"),
    ("raw_text", "Исходный текст"),
]


def build_passports_xlsx(passports: list[dict[str, Any]]) -> bytes:
    rows = [_headers_row()]
    rows.extend(_passport_row(passport) for passport in passports)

    workbook = io.BytesIO()
    with zipfile.ZipFile(workbook, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(rows))

    return workbook.getvalue()


def _headers_row() -> list[str]:
    return [label for _, label in HEADERS]


def _passport_row(passport: dict[str, Any]) -> list[str]:
    manufacturer_info = passport.get("manufacturer_info") or {}
    flattened = {
        **passport,
        "manufacturer_name": manufacturer_info.get("name"),
        "manufacturer_enterprise_name": manufacturer_info.get("enterprise_name"),
        "manufacturer_address": manufacturer_info.get("address"),
        "manufacturer_contacts": manufacturer_info.get("contacts"),
        "serial_numbers": _join_list(passport.get("serial_numbers")),
        "technical_specs": _format_mapping(passport.get("technical_specs")),
        "raw_text": _truncate(passport.get("raw_text"), 5000),
    }
    return [_to_cell_value(flattened.get(key)) for key, _ in HEADERS]


def _to_cell_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _join_list(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _format_mapping(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, dict):
        return "\n".join(f"{key}: {item}" for key, item in value.items())
    return str(value)


def _truncate(value: Any, max_length: int) -> str:
    text = _to_cell_value(value)
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def _worksheet_xml(rows: list[list[str]]) -> str:
    row_xml = []
    for row_idx, row in enumerate(rows, start=1):
        cells = []
        for col_idx, value in enumerate(row, start=1):
            ref = f"{_column_name(col_idx)}{row_idx}"
            style = ' s="1"' if row_idx == 1 else ""
            cells.append(
                f'<c r="{ref}" t="inlineStr"{style}><is><t>{_xml_text(value)}</t></is></c>'
            )
        row_xml.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="18"/>'
        '<cols>'
        '<col min="1" max="1" width="24" customWidth="1"/>'
        '<col min="2" max="19" width="28" customWidth="1"/>'
        '</cols>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _xml_text(value: str) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", value)
    return escape(cleaned, {'"': "&quot;"})


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Passports" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )


def _workbook_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font>'
        '</fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/>'
        '</cellXfs>'
        "</styleSheet>"
    )
