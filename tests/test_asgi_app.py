"""Тесты для ASGI приложения (uvicorn).

Эти тесты проверяют работу Dash приложения через ASGI интерфейс,
который используется uvicorn для запуска приложения.
Все тесты используют httpx.AsyncClient для выполнения HTTP запросов
к ASGI приложению без необходимости запуска реального сервера.
"""
import pytest
from urllib.parse import quote
from httpx import AsyncClient
from app.app import asgi_app
from app.pages.home import update_map
from app.services.data_loader import DataLoader


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


@pytest.mark.asyncio
async def test_home_page_map_callback_without_click():
    """Проверка callback карты без клика (первая загрузка)."""
    # Вызываем callback без clickData (None)
    fig, pathname, search = update_map(None)
    
    # Проверяем, что возвращается фигура
    assert fig is not None
    # Проверяем, что навигация не обновляется (dash.no_update)
    import dash
    assert pathname is dash.no_update or pathname is None
    assert search is dash.no_update or search is None


@pytest.mark.asyncio
async def test_home_page_map_callback_with_valid_click():
    """Проверка callback карты с валидным кликом на регион."""
    # Загружаем данные для получения валидного индекса региона
    gdf = DataLoader().gdf
    
    # Проверяем, что есть регионы в данных
    assert len(gdf) > 0, "Должны быть загружены регионы"
    
    # Создаем валидный clickData для первого региона
    first_region_idx = gdf.index[0]
    click_data = {
        "points": [
            {
                "location": first_region_idx,
            }
        ]
    }
    
    # Вызываем callback с clickData
    fig, pathname, search = update_map(click_data)
    
    # Проверяем, что возвращается фигура
    assert fig is not None
    
    # Проверяем, что навигация настроена правильно
    assert pathname == "/region", f"Ожидался pathname='/region', получен '{pathname}'"
    assert search is not None, "search не должен быть None"
    assert "region=" in search, f"search должен содержать 'region=', получен '{search}'"
    
    # Проверяем, что имя региона присутствует в search
    region_name = gdf.loc[first_region_idx]["name"]
    assert region_name is not None, "Имя региона не должно быть None"
    # Имя региона может быть закодировано в URL
    assert len(search) > len("?region="), "search должен содержать закодированное имя региона"


@pytest.mark.asyncio
async def test_region_page_with_valid_parameter():
    """Проверка доступности страницы региона с валидным параметром."""
    # Загружаем данные для получения валидного имени региона
    gdf = DataLoader().gdf
    
    # Проверяем, что есть регионы в данных
    assert len(gdf) > 0, "Должны быть загружены регионы"
    
    # Берем первое валидное имя региона
    first_region_name = gdf.iloc[0]["name"]
    assert first_region_name is not None, "Имя региона не должно быть None"
    
    # Кодируем имя региона для URL
    region_encoded = quote(first_region_name)
    
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        # Пробуем открыть страницу региона с валидным параметром
        response = await client.get(f"/region?region={region_encoded}")
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
        # Проверяем, что страница содержит информацию о регионе или сообщение об ошибке
        assert len(response.text) > 0, "Ответ не должен быть пустым"


@pytest.mark.asyncio
async def test_region_page_with_invalid_parameter():
    """Проверка обработки невалидного параметра региона."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        # Пробуем открыть страницу региона с несуществующим регионом
        response = await client.get("/region?region=НесуществующийРегион12345")
        assert response.status_code == 200, "Страница должна отвечать даже с невалидным параметром"
        # Проверяем, что отображается сообщение об ошибке или регион не найден
        assert "не найден" in response.text.lower() or "не указан" in response.text.lower() or "не выбран" in response.text.lower(), \
            "Должно отображаться сообщение об ошибке для невалидного региона"


@pytest.mark.asyncio
async def test_region_page_without_parameter():
    """Проверка обработки отсутствия параметра региона."""
    async with AsyncClient(app=asgi_app, base_url="http://test") as client:
        # Пробуем открыть страницу региона без параметра
        response = await client.get("/region")
        assert response.status_code == 200, "Страница должна отвечать даже без параметра"
        # Проверяем, что отображается сообщение о необходимости выбора региона
        assert "не выбран" in response.text.lower() or "не указан" in response.text.lower(), \
            "Должно отображаться сообщение о необходимости выбора региона"


@pytest.mark.asyncio
async def test_home_page_map_callback_with_invalid_index():
    """Проверка обработки некорректного индекса в clickData."""
    # Создаем clickData с несуществующим индексом
    invalid_index = 999999
    click_data = {
        "points": [
            {
                "location": invalid_index,
            }
        ]
    }
    
    # Вызываем callback - должно обработать ошибку корректно
    # (либо выбросить исключение, либо вернуть no_update)
    try:
        fig, pathname, search = update_map(click_data)
        # Если не выброшено исключение, проверяем результат
        assert fig is not None, "Фигура должна быть создана даже при ошибке"
    except (KeyError, IndexError):
        # Ожидаемое поведение при невалидном индексе
        pass
