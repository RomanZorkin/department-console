import dash
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
from urllib.parse import unquote_plus, parse_qs

from services.data_loader import load_data


dash.register_page(__name__)
# Загружаем данные один раз через сервисный слой, чтобы избежать циклических импортов
# и избыточных зависимостей страницы от конфигурации путей
# (regions_path используется только внутри сервиса данных).
gdf = load_data()

# Layout страницы
layout = html.Div(
    [
        dcc.Location(id="page-url", refresh=False),  # Для отслеживания URL
        html.Div(id="page-content"),  # Контейнер для контента
    ]
)


@callback(
    Output("page-content", "children"),  # ✅ Указали куда выводить
    Input("page-url", "search"),  # ✅ Используем наш компонент
    Input("page-url", "pathname"),
)
def update_page(search, pathname):
    # Проверяем наличие query string
    if not search or "region=" not in search:
        return html.Div(
            [
                html.H1("Регион не выбран"),
                html.P("Пожалуйста, выберите регион на главной странице"),
                html.A(
                    "← На главную",
                    href="/",
                    style={"color": "blue", "textDecoration": "underline"},
                ),
            ]
        )

    # Извлекаем параметр region
    query_params = parse_qs(search.lstrip("?"))
    region = query_params.get("region", [""])[0]

    if not region:
        return html.Div("Не указан регион")

    # Декодируем имя региона
    region = unquote_plus(region)

    # Ищем данные региона
    region_data = gdf[gdf["name"] == region]

    if region_data.empty:
        return html.Div(
            [
                html.H1("Регион не найден"),
                html.P(f"Регион '{region}' не найден в базе данных"),
                html.A("← На главную", href="/"),
            ]
        )

    row = region_data.iloc[0]

    # Создаем карту
    fig = go.Figure(
        go.Choroplethmapbox(
            geojson=region_data.geometry.__geo_interface__,
            locations=region_data.index,
            z=[row["value"]],
            colorscale="Viridis",  # Добавляем цвета
            text=[region],  # Текст для подсказки
            hovertemplate="<b>%{text}</b><br>Значение: %{z}<extra></extra>",
        )
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=5,  # Чуть увеличим масштаб
        mapbox_center={
            "lat": row.geometry.centroid.y,
            "lon": row.geometry.centroid.x,
        },
        margin=dict(l=0, r=0, t=0, b=0),
    )

    return html.Div(
        [
            html.H1(f"📊 Дашборд региона: {region}"),
            html.Div(
                [
                    html.P(f"📍 Название: {region}"),
                    html.P(f"📈 Значение: {row.get('value', 'Н/Д')}"),
                    html.P(
                        f"🌍 Координаты: {row.geometry.centroid.y:.4f}, {row.geometry.centroid.x:.4f}"
                    ),
                ],
                style={
                    "margin": "20px 0",
                    "padding": "15px",
                    "background": "#f8f9fa",
                    "borderRadius": "5px",
                },
            ),
            dcc.Graph(
                id="region-map",
                figure=fig,
                style={
                    "height": "70vh",
                    "width": "100%",
                    "border": "1px solid #ddd",
                    "borderRadius": "10px",
                },
            ),
            html.Div(
                [
                    html.A(
                        "← Вернуться к карте России",
                        href="/",
                        style={
                            "display": "inline-block",
                            "padding": "12px 24px",
                            "background": "#007bff",
                            "color": "white",
                            "textDecoration": "none",
                            "borderRadius": "5px",
                            "marginTop": "20px",
                            "fontWeight": "bold",
                        },
                    )
                ],
                style={"textAlign": "center", "marginTop": "30px"},
            ),
        ]
    )
