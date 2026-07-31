"""Pydantic-схемы для EquipmentType — справочник типов оборудования (read-only в рамках B09a)."""
import uuid

from pydantic import BaseModel, ConfigDict


class EquipmentTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
