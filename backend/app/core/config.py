"""
Конфигурация приложения через pydantic-settings.
Значения читаются из переменных окружения / файла .env
(имена переменных синхронизированы с корневым .env.example репозитория).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Секрет для аутентификации входящих интеграционных вебхуков (n8n/Zabbix/OpenProject)
    # и /api/my/tickets (доступ MAX-бота) — заголовок X-Webhook-Secret, см. п. 4.6 ТЗ
    WEBHOOK_SECRET: str

    # PostgreSQL
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Redis
    REDIS_PORT: int = 6379
    REDIS_HOST: str = "redis"

    # JWT / безопасность
    SECRET_KEY: str
    JWT_ACCESS_TTL_MIN: int = 15
    JWT_REFRESH_TTL_DAYS: int = 7

    # CORS — список origin'ов через запятую, без пробелов
    # (прод: https://it.example-hospital.ru; локально: http://127.0.0.1:3000)
    CORS_ORIGINS: str = ""

    # MinIO (вложения к заявкам, сессия B10a)
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_PUBLIC_ENDPOINT: str = "http://127.0.0.1:9000"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_TICKETS: str = "tickets-attachments"
    MAX_ATTACHMENT_SIZE_MB: int = 10

    # Zabbix (мониторинг, сессия B11 — см. TZ п. 6.1)
    ZABBIX_URL: str = "http://192.168.10.21:8081/api_jsonrpc.php"
    ZABBIX_API_TOKEN: str = ""

    # Secure-флаг refresh-cookie: True по умолчанию (требование ТЗ раздел 7 для прода),
    # False — только для локальной разработки по HTTP без TLS
    REFRESH_COOKIE_SECURE: bool = True

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()  # type: ignore[call-arg]  # pydantic-settings подставляет поля из .env в рантайме
