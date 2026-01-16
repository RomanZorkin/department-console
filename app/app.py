import dash
from dash import Dash, html, dcc
from asgiref.wsgi import WsgiToAsgi

app = Dash(
    __name__,
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
        dash.page_container,
    ]
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
