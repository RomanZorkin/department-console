from __future__ import annotations

from typing import Any, List, Literal, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalyticRecord(BaseModel):
    """Строка из CSV app/data/analytic/data.csv.

    Ожидаемые поля соответствуют заголовку файла data.csv.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    region_name: str = Field(..., description="")
    region: str = Field(..., description="Название региона для связывания с GeoJSON (поле name)")
    value: float
    percent_change: float
    budget_millions: float
    population_change: float
    details: str


class GeoJSONGeometry(BaseModel):
    """Упрощённое описание geometry из GeoJSON.

    Для текущих файлов достаточно валидировать тип и формат координат,
    не вдаваясь в детали конкретной проекции.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    type: Literal["Polygon", "MultiPolygon"]
    coordinates: Any  # сложная вложенная структура, проверяется частично ниже

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: Any) -> Any:
        # Базовая проверка: это должно быть вложенным списком чисел
        if not isinstance(v, list):
            raise ValueError("coordinates must be a list")
        # Глубокую геометрическую валидацию оставляем на сторону GeoPandas/Shapely
        return v


class GeoJSONFeatureProperties(BaseModel):
    """Свойства объекта из отдельных региональных GeoJSON файлов.

    Пример (Adygeya.geojson):
    {
      "name": "Республика Адыгея",
      "cartodb_id": 37,
      "created_at": "2013-12-04T04:23:51+0100",
      "updated_at": "2013-12-04T08:09:06+0100",
      "name_latin": "Republic of Adygea"
    }
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str
    cartodb_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    name_latin: Optional[str] = None


class GeoJSONFeature(BaseModel):
    """Единственный Feature из файлам app/data/regions/*.geojson."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["Feature"]
    properties: GeoJSONFeatureProperties
    geometry: GeoJSONGeometry


class GeoJSONFeatureCollection(BaseModel):
    """FeatureCollection из файлов config/russia_regions.geojson и т.п."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["FeatureCollection"]
    features: List[GeoJSONFeature]


def validate_analytic_dataframe(df: pd.DataFrame) -> List[AnalyticRecord]:
    """Провалидировать DataFrame с данными аналитики.

    При первой ошибке структуры будет выброшен pydantic.ValidationError.
    Возвращает список Pydantic‑моделей.
    """

    records: List[AnalyticRecord] = []

    for _, row in df.iterrows():
        data = row.to_dict()
        record = AnalyticRecord.model_validate(data)
        records.append(record)

    return records


def validate_geojson_feature(data: dict) -> GeoJSONFeature:
    """Провалидировать одиночный GeoJSON Feature (как в Adygeya.geojson)."""

    return GeoJSONFeature.model_validate(data)


def validate_geojson_feature_collection(data: dict) -> GeoJSONFeatureCollection:
    """Провалидировать GeoJSON FeatureCollection."""

    return GeoJSONFeatureCollection.model_validate(data)
