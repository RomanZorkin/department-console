"""Тесты для ASGI приложения (uvicorn).

Эти тесты проверяют работу Dash приложения через ASGI интерфейс,
который используется uvicorn для запуска приложения.
Все тесты используют httpx.AsyncClient для выполнения HTTP запросов
к ASGI приложению без необходимости запуска реального сервера.
"""
import pytest
from httpx import AsyncClient
from app.app import asgi_app


@pytest.mark.asyncio
async def test_asgi_app_exists():
    """Проверка, что ASGI приложение создано."""
    assert asgi_app is not None


@pytest.mark.asyncio
async def test_asgi_app_root_path():
    """Проверка доступности корневого пути через ASGI."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_asgi_app_home_page():
    """Проверка доступности главной страницы."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        # Проверяем, что в ответе есть заголовок страницы
        assert "Карта России" in response.text or "Multi-page app" in response.text


@pytest.mark.asyncio
async def test_asgi_app_region_page():
    """Проверка доступности страницы региона."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        # Пробуем открыть страницу региона (может быть пустой, но должна отвечать)
        response = await client.get("/region")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_asgi_app_static_assets():
    """Проверка доступности статических ресурсов Dash."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        # Dash обычно обслуживает статику через /_dash-component-suites/
        # Проверяем, что запрос не приводит к критической ошибке
        response = await client.get("/_dash-component-suites/")
        # Может быть 404 или 200, но не 500
        assert response.status_code != 500


@pytest.mark.asyncio
async def test_asgi_app_404():
    """Проверка обработки несуществующих путей."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        response = await client.get("/nonexistent-page")
        # Dash может возвращать 200 с редиректом или 404
        assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_asgi_app_response_headers():
    """Проверка наличия необходимых заголовков в ответе."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        response = await client.get("/")
        assert "content-type" in response.headers
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_asgi_app_multiple_requests():
    """Проверка стабильности при множественных запросах."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        # Выполняем несколько запросов подряд
        for _ in range(5):
            response = await client.get("/")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_asgi_app_health_check():
    """Проверка работоспособности приложения (health check)."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        response = await client.get("/")
        # Приложение должно отвечать на запросы
        assert response.status_code == 200
        # Проверяем, что ответ не пустой
        assert len(response.content) > 0
