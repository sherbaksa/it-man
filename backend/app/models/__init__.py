"""Реестр моделей — импортируется в alembic/env.py для автогенерации миграций."""
from app.models.asset import Asset
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.department import Department
from app.models.document_template import DocumentTemplate
from app.models.equipment_type import EquipmentType
from app.models.integration_log import IntegrationLog
from app.models.monitoring_status import MonitoringStatus
from app.models.movement import Movement
from app.models.order import Order
from app.models.order_history import OrderHistory
from app.models.repair import Repair
from app.models.ticket import Ticket
from app.models.user import User

__all__ = [
    "Department",
    "EquipmentType",
    "User",
    "Asset",
    "Movement",
    "Repair",
    "Ticket",
    "DocumentTemplate",
    "Order",
    "OrderHistory",
    "MonitoringStatus",
    "IntegrationLog",
    "AuditLog",
    "Attachment",
]