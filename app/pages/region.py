import logging

import dash
from dash import html, dcc, callback, Input, Output
from plotly import graph_objects as go
from urllib.parse import unquote_plus, parse_qs
import pandas as pd

from app.services.data_loader import DataLoader

# Настройка логирования безопасности
security_logger = logging.getLogger("security")


dash.register_page(__name__, name="Регион")
# Загружаем данные один раз через сервисный слой, чтобы избежать циклических импортов
# и избыточных зависимостей страницы от конфигурации путей
# (regions_path используется только внутри сервиса данных).
gdf = DataLoader().gdf
# Создаем whitelist допустимых регионов для валидации входных данных
VALID_REGIONS = set(gdf["name"].dropna().unique())

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
)
def update_page(search):  # noqa: ARG001
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
    region_input = query_params.get("region", [""])[0]

    if not region_input:
        return html.Div("Не указан регион")

    # Валидация входных данных: ограничение длины для защиты от DoS
    MAX_REGION_NAME_LENGTH = 200
    if len(region_input) > MAX_REGION_NAME_LENGTH:
        security_logger.warning(
            "Попытка доступа с слишком длинным параметром region: длина %s символов",
            len(region_input),
        )
        return html.Div(
            [
                html.H1("Ошибка валидации"),
                html.P("Недопустимый параметр региона"),
                html.A(
                    "← На главную",
                    href="/",
                    style={"color": "blue", "textDecoration": "underline"},
                ),
            ]
        )

    # Декодируем имя региона
    region_input = unquote_plus(region_input)

    # Валидация: проверяем, что регион существует в whitelist
    # Это защищает от XSS и path traversal атак
    if region_input not in VALID_REGIONS:
        security_logger.warning(
            "Попытка доступа к несуществующему региону: '%s' (возможная XSS или path traversal атака)",
            region_input,
        )
        return html.Div(
            [
                html.H1("Регион не найден"),
                html.P("Указанный регион не найден в базе данных"),
                html.A(
                    "← На главную",
                    href="/",
                    style={"color": "blue", "textDecoration": "underline"},
                ),
            ]
        )

    # Ищем данные региона (используем валидированное значение)
    region_data = gdf[gdf["name"] == region_input]

    # Безопасное имя региона из данных (не из пользовательского ввода)
    # Это дополнительная защита от XSS
    region = region_data.iloc[0]["name"] if not region_data.empty else region_input

    # Эта проверка не должна сработать после валидации выше,
    # но оставляем для дополнительной защиты
    if region_data.empty:
        return html.Div(
            [
                html.H1("Регион не найден"),
                html.P("Регион не найден в базе данных"),
                html.A(
                    "← На главную",
                    href="/",
                    style={"color": "blue", "textDecoration": "underline"},
                ),
            ]
        )

    row = region_data.iloc[0]
    centroid_y = row.geometry.centroid.y
    centroid_x = row.geometry.centroid.x

    # Получаем данные для столбчатой диаграммы (в процентах)
    staffing = row.get("staffing", 0) * 100 if pd.notna(row.get("staffing")) else 0
    cash_use = row.get("cash_use", 0) * 100 if pd.notna(row.get("cash_use")) else 0
    serviceability = row.get("serviceability", 0) * 100 if pd.notna(row.get("serviceability")) else 0

    # Функция для определения современного цвета по тем же правилам, что и в home.py
    # Границы: менее 0.7 (70%) - красный, 0.7-0.85 (70-85%) - желтый, 0.85-1 (85-100%) - зеленый
    def get_color(value_normalized):
        """Определяет современный цвет на основе нормализованного значения (0-1)."""
        if value_normalized < 0.7:  # noqa: WPS459 Сравнение с float необходимо для пороговых значений метрик
            return "#ef4444"  # Современный красный
        elif value_normalized < 0.85:  # noqa: WPS459 Сравнение с float необходимо для пороговых значений метрик
            return "#f59e0b"  # Современный оранжевый/янтарный
        else:
            return "#10b981"  # Современный зеленый

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

    # Создаем современную столбчатую диаграмму
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Укомплектованность", "Освоение ДС", "Исправность техники"],
                y=[staffing, cash_use, serviceability],
                marker=dict(
                    color=colors,
                    line=dict(
                        color=[c for c in colors],
                        width=2.5,
                    ),
                    opacity=0.9,
                ),
                text=[f"{staffing:.1f}%", f"{cash_use:.1f}%", f"{serviceability:.1f}%"],
                textposition="outside",
                textfont=dict(
                    size=14,
                    color="#1f2937",
                    family="Arial, sans-serif",
                    weight="bold",
                ),
                hovertemplate="<b>%{x}</b><br>" + "Значение: %{y:.1f}%<extra></extra>",
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#e5e7eb",
                    font_size=13,
                    font_family="Arial, sans-serif",
                ),
            )
        ]
    )

    # Современный стильный layout
    fig.update_layout(
        title=dict(
            text="📊 Показатели региона",
            font=dict(
                size=24,
                color="#111827",
                family="Arial, sans-serif",
                weight="bold",
            ),
            x=0.5,
            xanchor="center",
            pad=dict(t=20, b=30),
        ),
        xaxis=dict(
            title=dict(
                text="Показатель",
                font=dict(size=14, color="#6b7280", family="Arial, sans-serif"),
            ),
            tickfont=dict(size=12, color="#4b5563", family="Arial, sans-serif"),
            gridcolor="#e5e7eb",
            gridwidth=1,
            showline=True,
            linecolor="#d1d5db",
            linewidth=1,
        ),
        yaxis=dict(
            title=dict(
                text="Процент (%)",
                font=dict(size=14, color="#6b7280", family="Arial, sans-serif"),
            ),
            tickfont=dict(size=12, color="#4b5563", family="Arial, sans-serif"),
            range=[0, 100],
            gridcolor="#e5e7eb",
            gridwidth=1,
            showline=True,
            linecolor="#d1d5db",
            linewidth=1,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=40, t=80, b=60),
        height=450,
        showlegend=False,
        hovermode="closest",
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
                    "height": "550px",
                    "width": "100%",
                    "border": "none",
                    "borderRadius": "16px",
                    "marginTop": "20px",
                    "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
                    "backgroundColor": "white",
                    "padding": "20px",
                },
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": f"dashboard_{region}",
                        "height": 600,
                        "width": 1200,
                        "scale": 2,
                    },
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
