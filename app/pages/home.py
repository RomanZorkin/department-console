import dash
from dash import dcc, html, Input, Output, callback
from plotly import graph_objects as go
from urllib.parse import quote
from services.data_loader import load_data


dash.register_page(__name__, path="/")

# Загружаем данные один раз при запуске
gdf = load_data()

# Layout страницы
layout = html.Div(
    [
        dcc.Location(id="url", refresh=True),
        html.H1("Карта России", style={"textAlign": "center"}),
        html.Div(
            [
                html.Label("Выберите год:", style={"marginRight": "10px"}),
                dcc.Slider(
                    id="year-slider",
                    min=2000,
                    max=2023,
                    value=2023,
                    marks={i: str(i) for i in range(2000, 2024, 5)},
                    step=1,
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
            ],
            style={"margin": "20px"},
        ),
        dcc.Graph(id="choropleth", style={"height": "70vh"}),
    ]
)


# Callback для обновления карты
@callback(
    Output("choropleth", "figure"),
    Output("url", "href"),
    Input("year-slider", "value"),
    Input("choropleth", "clickData"),
)
def update_map(year, clickData):
    """Обновить карту по выбранному году.

    На карте:
    * показываются границы **всех** регионов;
    * регионы **с данными** залиты цветом с прозрачностью ~50%;
    * регионы **без данных** отображаются только границами (без заливки).
    """

    # Фильтруем по году, если столбец year присутствует
    if "year" in gdf.columns and "value" in gdf.columns:
        gdf_filtered = gdf[gdf["year"] == year]
    else:
        gdf_filtered = gdf

    # Разделяем регионы на с данными и без данных (по столбцу value)
    if "value" in gdf_filtered.columns:
        gdf_with_data = gdf_filtered[gdf_filtered["value"].notna()]
        gdf_without_data = gdf_filtered[gdf_filtered["value"].isna()]
    else:
        # Если аналитических данных нет вообще — считаем, что данных нет ни у одного региона
        gdf_with_data = gdf_filtered.iloc[:0]
        gdf_without_data = gdf_filtered

    geojson_all = gdf_filtered.__geo_interface__

    fig = go.Figure()

    # Трейс для регионов с данными: полигон с полупрозрачной заливкой
    if not gdf_with_data.empty:
        fig.add_trace(
            go.Choroplethmapbox(
                geojson=geojson_all,
                locations=gdf_with_data.index,
                z=(
                    gdf_with_data["value"]
                    if "value" in gdf_with_data.columns
                    else [1 for _ in range(len(gdf_with_data))]
                ),
                text=gdf_with_data["name"],
                colorscale="RdYlGn",
                colorbar_title="Значение",
                hovertemplate=(
                    "<b>%{text}</b><br>Значение: %{z}<br><extra></extra>"
                ),
                marker_opacity=0.5,  # полупрозрачная заливка
                marker_line_width=0.5,
                marker_line_color="black",
            ),
        )

    # Трейс для регионов без данных: только границы, заливка прозрачная
    if not gdf_without_data.empty:
        fig.add_trace(
            go.Choroplethmapbox(
                geojson=geojson_all,
                locations=gdf_without_data.index,
                z=[0 for _ in range(len(gdf_without_data))],
                text=gdf_without_data["name"],
                # полностью прозрачная палитра
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                showscale=False,
                hovertemplate=(
                    "<b>%{text}</b><br>Нет данных<br><extra></extra>"
                ),
                marker_opacity=0,  # нет заливки
                marker_line_width=0.5,
                marker_line_color="gray",
            ),
        )

    # Настройки карты
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=2.5,
        mapbox_center={"lat": 61.698653, "lon": 99.505405},
        margin=dict(l=0, r=0, t=30, b=0),
        height=600,
    )

    href = dash.no_update
    if clickData:
        # В clickData для choroplethmapbox индекс региона содержится в поле "location"
        region_idx = clickData["points"][0]["location"]
        region_name = gdf.loc[region_idx]["name"]
        region_encoded = quote(region_name)
        href = f"/region?region={region_encoded}"

    return fig, href
