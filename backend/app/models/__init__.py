"""Реестр моделей — импортируется в alembic/env.py для автогенерации миграций."""
from app.models.asset import Asset
from app.models.department import Department
from app.models.equipment_type import EquipmentType
from app.models.user import User

__all__ = ["Department", "EquipmentType", "User", "Asset"]