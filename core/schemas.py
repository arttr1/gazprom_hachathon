"""Pydantic-схемы для структурированного результата оцифровки паспортов.

Здесь описаны модели данных, которые должны заполняться после обработки документа.
Схемы используются одновременно как:
- контракт между OCR/LLM и приложением,
- источник JSON Schema для structured output в LLM,
- формат данных для сохранения и интеграции с внешними системами.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional
from datetime import date


class ManufacturerInfo(BaseModel):
    """Детальные сведения о производителе оборудования."""

    name: str = Field(..., description="Краткое имя производителя (бренд)")
    enterprise_name: str = Field(..., description="Полное наименование предприятия")
    address: str = Field(..., description="Юридический или фактический адрес")
    contacts: str = Field(..., description="Контакты: телефон, email, сайт и т.п.")


class PassportData(BaseModel):
    """Итоговая структура данных одного паспорта оборудования."""

    equipment_number: str = Field(..., description="Номер оборудования")
    manufacturer: str = Field(..., description="Производитель (кратко)")
    manufacturer_info: ManufacturerInfo = Field(
        ..., description="Подробная информация о производителе"
    )
    model: str = Field(..., description="Модель / наименование изделия")
    order_code: Optional[str] = Field(None, description="Код заказа")
    serial_numbers: List[str] = Field(default_factory=list, description="Заводские номера")
    technical_specs: Dict[str, Any] = Field(default_factory=dict, description="Технические характеристики")
    temperature_range: Optional[str] = None
    manufacture_date: Optional[date] = None
    guarantee_months: Optional[int] = None
    acceptance_date: Optional[date] = None
    otk_person: Optional[str] = None
    executive_system: Optional[str] = None
    raw_text: Optional[str] = None