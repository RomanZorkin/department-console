import dash
from dash import Dash, html, dcc
from asgiref.wsgi import WsgiToAsgi
from flask import Flask

# Создаем Flask приложение с настройками безопасности
flask_app = Flask(__name__)

# Настройка CORS: разрешаем только запросы с того же домена
# Для production можно настроить конкретные домены
@flask_app.after_request
def set_security_headers(response):
    """Установка security headers для защиты от различных атак."""
    # Защита от XSS атак
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Защита от clickjacking
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # Защита от MIME type sniffing
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Strict Transport Security (для HTTPS)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Content Security Policy
    # Разрешаем доступ к ресурсам для карт (Mapbox, OpenStreetMap, Plotly)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.plot.ly https://api.mapbox.com; "
        "style-src 'self' 'unsafe-inline' https://api.mapbox.com; "
        "img-src 'self' data: https: https://*.tile.openstreetmap.org https://api.mapbox.com; "
        "font-src 'self' data: https://cdn.plot.ly; "
        "connect-src 'self' https://api.mapbox.com https://*.tile.openstreetmap.org https://cdn.plot.ly; "
        "worker-src 'self' blob:;"
    )
    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app = Dash(
    __name__,
    server=flask_app,
    use_pages=True,
    suppress_callback_exceptions=True,
)

app.layout = html.Div(
    [
        html.H1("Multi-page app with Dash Pages"),
        html.Div(
            [
                html.Div(
                    dcc.Link(
                        f"{page['name']} - {page['path']}", href=page["relative_path"]
                    )
                )
                for page in dash.page_registry.values()
            ]
        ),
        dcc.Location(id="url", refresh=False),
        html.Div(id="redirect-url", style={"display": "none"}),  # Глобальный компонент для навигации
        dash.page_container,
    ]
)

# Клиентский callback для навигации при клике на карту
app.clientside_callback(
    """
    function(url) {
        if (url && url !== "") {
            window.location.href = url;
        }
        return window.location.pathname;
    }
    """,
    dash.dependencies.Output("url", "pathname"),
    dash.dependencies.Input("redirect-url", "children"),
    prevent_initial_call=True,
)

# ASGI приложение для uvicorn
asgi_app = WsgiToAsgi(app.server)

if __name__ == "__main__":
    import uvicorn
    from app.config import UVICORN_HOST, UVICORN_PORT, UVICORN_RELOAD

    uvicorn.run(
        asgi_app,
        host=UVICORN_HOST,
        port=UVICORN_PORT,
        reload=UVICORN_RELOAD,
    )
