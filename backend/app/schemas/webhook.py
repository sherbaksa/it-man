"""Pydantic-схемы для входящих интеграционных вебхуков (п. 4.6 ТЗ).

ZabbixWebhookPayload — контракт, который МЫ задаём для Zabbix Action -> Webhook
(шаблон сообщения настраивается в самом Zabbix, см. открытый вопрос №5 ТЗ /
риски сессии B13) — до реальной настройки Zabbix Action тестируется вручную
через curl синтетическим payload.
"""
import enum

from pydantic import BaseModel, Field


class ZabbixSeverity(str, enum.Enum):
    NOT_CLASSIFIED = "not_classified"
    INFORMATION = "information"
    WARNING = "warning"
    AVERAGE = "average"
    HIGH = "high"
    DISASTER = "disaster"


class ZabbixProblemStatus(str, enum.Enum):
    PROBLEM = "PROBLEM"
    RESOLVED = "RESOLVED"


class ZabbixWebhookPayload(BaseModel):
    host: str = Field(
        ..., description="Host identifier (host name/IP) из Zabbix — соответствует MonitoringStatus.host_identifier"
    )
    severity: ZabbixSeverity
    status: ZabbixProblemStatus
    problem_name: str = Field(..., description="Название триггера/проблемы (Zabbix {EVENT.NAME})")
    event_id: str | None = Field(
        None,
        description="{EVENT.ID} Zabbix — задел под идемпотентность повторных вызовов, в B13 не используется (см. известные проблемы отчёта)",
    )
