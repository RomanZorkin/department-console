from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from pydantic import ValidationError

from config import regions_path
from models import validate_analytic_dataframe, validate_geojson_feature


class DataLoader:
    """Загрузчик и валидатор геоданных и аналитических данных.

    Логика, ранее реализованная через набор функций, инкапсулирована в класс,
    чтобы упростить переиспользование и возможное расширение (другие
    источники данных, разные пути и т.п.).
    """

    def __init__(self, regions_dir: Path | None = None) -> None:
        # По умолчанию используем путь из конфигурации
        self.regions_dir = regions_dir or regions_path

    @staticmethod
    def _convert_to_lists(obj: Any) -> Any:
        """Рекурсивно конвертировать tuples в lists, чтобы соответствовать GeoJSON."""
        if isinstance(obj, tuple):
            return [DataLoader._convert_to_lists(item) for item in obj]
        if isinstance(obj, list):
            return [DataLoader._convert_to_lists(item) for item in obj]
        return obj

    @staticmethod
    def _load_and_validate_geojson_file(path: Path) -> gpd.GeoDataFrame:
        """Загрузить один .geojson файл, провалидировав его через Pydantic.

        Ожидается структура, аналогичная файлам в ``app/data/regions``
        (например, ``Adygeya.geojson``): один GeoJSON Feature в корне.
        """

        # GeoPandas читает файл сразу как GeoDataFrame; чтобы валидировать
        # структуру, читаем его сырым JSON и пропускаем через Pydantic‑модель.
        raw = gpd.read_file(path)

        # В большинстве региональных файлов ожидается один Feature.
        if len(raw) != 1:
            raise ValueError(
                f"GeoJSON {path} должен содержать один объект, получено: {len(raw)}",
            )

        # GeoPandas возвращает DataFrame, где каждая строка — Feature, а все
        # негеометрические колонки — свойства. Преобразуем первую строку в dict
        # и собираем структуру уровня Feature.
        row = raw.iloc[0]
        properties = row.drop(labels=["geometry"]).to_dict()

        # Конвертировать Timestamp в str для совместимости с Pydantic
        for key, value in properties.items():
            if isinstance(value, pd.Timestamp):
                properties[key] = value.isoformat()

        geometry_dict = row["geometry"].__geo_interface__
        # Конвертировать tuples в lists, чтобы соответствовать GeoJSON
        geometry_dict["coordinates"] = DataLoader._convert_to_lists(
            geometry_dict["coordinates"],
        )

        feature_dict = {
            "type": "Feature",
            "properties": properties,
            "geometry": geometry_dict,
        }

        # Pydantic проверит, что есть поля name, geometry и т.д.
        validate_geojson_feature(feature_dict)

        # Если валидация успешна, возвращаем исходный GeoDataFrame для этого файла
        return raw

    @staticmethod
    def _load_and_validate_analytic_data(path: Path) -> pd.DataFrame:
        """Загрузить CSV с аналитикой и провалидировать каждую строку."""

        df = pd.read_csv(path)

        try:
            # Возвращаем DataFrame, соответствующий списку валидных Pydantic‑моделей.
            records = validate_analytic_dataframe(df)
        except ValidationError as exc:
            raise ValidationError.from_exception_data(
                "AnalyticRecordDataFrame",
                exc.errors(),
            ) from exc

        # Преобразуем обратно в DataFrame; столбцы и их типы определяются
        # Pydantic‑моделью AnalyticRecord.
        valid_df = pd.DataFrame([r.model_dump() for r in records])
        return valid_df

    def create_gdf(self) -> gpd.GeoDataFrame:
        """Создать GeoDataFrame с объединёнными геометриями и аналитическими данными.

        1. Для каждого .geojson файла в каталоге ``regions_dir``:
           * загружаем данные;
           * валидируем структуру через Pydantic‑модель GeoJSONFeature;
           * добавляем в общий GeoDataFrame.
        2. Загружаем ``data.csv`` и валидируем каждую строку через AnalyticRecord.
        3. Мерджим по имени региона: ``name`` (GeoJSON) == ``region`` (CSV).
        """

        gdf_data: list[gpd.GeoDataFrame] = []

        for region_json in self.regions_dir.iterdir():
            if region_json.suffix != ".geojson":
                continue

            gdf = self._load_and_validate_geojson_file(region_json)
            gdf_data.append(gdf)

        if not gdf_data:
            raise ValueError(
                f"В каталоге {self.regions_dir} не найдено ни одного .geojson файла",
            )

        json_df = pd.concat(gdf_data, ignore_index=True)
        json_df = gpd.GeoDataFrame(json_df)
        json_df.dropna(inplace=True, axis=1)

        # Удаляем возможные дубликаты по названию региона, чтобы в результирующем
        # GeoDataFrame имена были уникальны
        json_df = json_df.drop_duplicates(subset="name")

        data_csv_path = (
            Path(__file__).resolve().parent.parent / "data" / "analytic" / "data.csv"
        )
        analytic_df = self._load_and_validate_analytic_data(data_csv_path)

        # Ожидается, что столбец 'name' в GeoJSON соответствует столбцу 'region' в CSV
        merged = json_df.merge(analytic_df, left_on="name", right_on="region", how="left")

        return merged

    def load_data(self) -> gpd.GeoDataFrame:
        """Загрузить GeoDataFrame по умолчанию, используя установленный путь."""

        return self.create_gdf()


# Сохранение прежнего процедурного API для обратной совместимости
_default_loader = DataLoader()


def create_gdf(regions_path: Path) -> gpd.GeoDataFrame:
    """Обёртка над [`DataLoader.create_gdf()`](app/services/data_loader.py:86) для обратной совместимости.

    Параметр ``regions_path`` принимает приоритет над значением из конфигурации.
    """

    loader = DataLoader(regions_dir=regions_path)
    return loader.create_gdf()


def load_data() -> gpd.GeoDataFrame:
    """Загрузить GeoDataFrame по умолчанию, используя путь из конфигурации.

    Обёртка над [`DataLoader.load_data()`](app/services/data_loader.py:113) для обратной совместимости.
    """

    return _default_loader.load_data()
