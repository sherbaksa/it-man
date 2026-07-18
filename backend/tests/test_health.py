"""
Тест health-check эндпоинта.

Проверяет базовую доступность backend-приложения — используется
как минимальный smoke-тест, пока основной набор тестов ещё не написан
(полноценные тесты auth/users появятся в сессии B05).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
