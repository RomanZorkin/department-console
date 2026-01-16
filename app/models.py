from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ============================================================================
# CSV Data Models
# ============================================================================


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


class OrganizationRecord(BaseModel):
    """Строка из CSV app/data/analytic/organizations.csv.

    Ожидаемые поля соответствуют заголовку файла organizations.csv.
    Валидирует правила:
    - by_list <= by_staff
    - cash_execution <= buget_limits
    - faulty_equipment <= equipment
    - Все значения от 0 до 100
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    city: str = Field(..., description="Город нахождения организации")
    region: str = Field(..., description="Регион нахождения организации")
    by_staff: int = Field(..., ge=0, le=100, description="Кол-во людей в штатном расписании")
    by_list: int = Field(..., ge=0, le=100, description="Фактическое количество работников")
    buget_limits: int = Field(..., ge=0, le=100, description="Выделенные лимиты расходов")
    cash_execution: int = Field(..., ge=0, le=100, description="Фактически израсходовано")
    equipment: int = Field(..., ge=0, le=100, description="Всего техники в наличии")
    faulty_equipment: int = Field(..., ge=0, le=100, description="Сломанная техника")

    @model_validator(mode="after")
    def validate_dependencies(self) -> "OrganizationRecord":
        """Проверка зависимостей между полями."""
        if self.by_list > self.by_staff:
            raise ValueError(
                f"by_list ({self.by_list}) не может быть больше by_staff ({self.by_staff})"
            )
        if self.cash_execution > self.buget_limits:
            raise ValueError(
                f"cash_execution ({self.cash_execution}) не может быть больше "
                f"buget_limits ({self.buget_limits})"
            )
        if self.faulty_equipment > self.equipment:
            raise ValueError(
                f"faulty_equipment ({self.faulty_equipment}) не может быть больше "
                f"equipment ({self.equipment})"
            )
        return self


# ============================================================================
# GeoJSON Models
# ============================================================================


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


