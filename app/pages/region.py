import dash
from dash import html, dcc, callback, Input, Output
from plotly import graph_objects as go
from urllib.parse import unquote_plus, parse_qs
import pandas as pd

from app.services.data_loader import DataLoader


dash.register_page(__name__)
# Загружаем данные один раз через сервисный слой, чтобы избежать циклических импортов
# и избыточных зависимостей страницы от конфигурации путей
# (regions_path используется только внутри сервиса данных).
gdf = DataLoader().gdf

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
def update_page(search, pathname):  # noqa: ARG001
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
    centroid_y = row.geometry.centroid.y
    centroid_x = row.geometry.centroid.x

    # Получаем данные для столбчатой диаграммы (в процентах)
    staffing = row.get("staffing", 0) * 100 if pd.notna(row.get("staffing")) else 0
    cash_use = row.get("cash_use", 0) * 100 if pd.notna(row.get("cash_use")) else 0
    serviceability = row.get("serviceability", 0) * 100 if pd.notna(row.get("serviceability")) else 0

    # Функция для определения цвета по тем же правилам, что и в home.py
    # Границы: менее 0.7 (70%) - красный, 0.7-0.85 (70-85%) - желтый, 0.85-1 (85-100%) - зеленый
    def get_color(value_normalized):
        """Определяет цвет на основе нормализованного значения (0-1)."""
        if value_normalized < 0.7:
            return "red"
        elif value_normalized < 0.85:
            return "yellow"
        else:
            return "green"

    # Нормализуем значения для определения цвета (из процентов обратно в 0-1)
    staffing_norm = staffing / 100
    cash_use_norm = cash_use / 100
    serviceability_norm = serviceability / 100

    # Определяем цвета для каждого столбца
    colors = [
        get_color(staffing_norm),
        get_color(cash_use_norm),
        get_color(serviceability_norm),
    ]

    # Создаем столбчатую диаграмму
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Укомплектованность", "Освоение ДС", "Исправность техники"],
                y=[staffing, cash_use, serviceability],
                marker_color=colors,
                text=[f"{staffing:.1f}%", f"{cash_use:.1f}%", f"{serviceability:.1f}%"],
                textposition="outside",
            )
        ]
    )

    fig.update_layout(
        title="Показатели региона",
        xaxis_title="Показатель",
        yaxis_title="Процент (%)",
        yaxis=dict(range=[0, 100]),
        margin=dict(l=20, r=20, t=50, b=20),
        height=400,
    )

    return html.Div(
        [
            html.H1(f"📊 Дашборд региона: {region}"),
            html.Div(
                [
                    html.P(f"📍 Регион: {region}"),
                    html.P(f"📈 Укомплектованность: {staffing:.1f} %"),
                    html.P(f"📈 Освоение ДС: {cash_use:.1f} %"),
                    html.P(f"📈 Исправность техники: {serviceability:.1f}%"),
                    html.P(
                        f"🌍 Координаты: {centroid_y:.4f}, {centroid_x:.4f}"
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
                id="region-chart",
                figure=fig,
                style={
                    "height": "500px",
                    "width": "100%",
                    "border": "1px solid #ddd",
                    "borderRadius": "10px",
                    "marginTop": "20px",
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
