import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from app.models import GeoJSONFeature

# Настройка логирования безопасности
security_logger = logging.getLogger("security")

# Максимальный размер файла: 100 МБ (в байтах)
MAX_FILE_SIZE = 100 * 1024 * 1024


def _convert_to_lists(obj: Any) -> Any:
    """Рекурсивно конвертировать tuples в lists, чтобы соответствовать GeoJSON."""
    if isinstance(obj, tuple):
        return [_convert_to_lists(item) for item in obj]
    if isinstance(obj, list):
        return [_convert_to_lists(item) for item in obj]
    return obj


def load_and_validate_geojson_file(path: Path) -> gpd.GeoDataFrame:
    """Загрузить один .geojson файл, провалидировав его через Pydantic.

    Ожидается структура, аналогичная файлам в ``app/data/regions``
    (например, ``Adygeya.geojson``): один GeoJSON Feature в корне.

    Args:
        path: Путь к GeoJSON файлу.

    Returns:
        GeoDataFrame с валидированными данными.

    Raises:
        ValueError: Если размер файла превышает максимально допустимый.
    """
    # Валидация размера файла для защиты от DoS атак
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        security_logger.warning(
            "Попытка загрузки файла превышающего максимальный размер: %s, размер: %s байт",
            path,
            file_size,
        )
        raise ValueError(
            f"Размер файла {file_size} байт превышает максимально допустимый {MAX_FILE_SIZE} байт",
        )

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
    geometry_dict["coordinates"] = _convert_to_lists(
        geometry_dict["coordinates"],
    )

    feature_dict = {
        "type": "Feature",
        "properties": properties,
        "geometry": geometry_dict,
    }

    # Pydantic проверит, что есть поля name, geometry и т.д.
    GeoJSONFeature.model_validate(feature_dict)

    # Если валидация успешна, возвращаем исходный GeoDataFrame для этого файла
    return raw


class GeoJSONLoader:
    """Загрузчик и валидатор GeoJSON файлов.

    Поддерживает загрузку GeoJSON файлов с валидацией через Pydantic модели.
    """

    def __init__(self, regions_dir: Path | None = None) -> None:
        """Инициализация загрузчика GeoJSON.

        Args:
            regions_dir: Каталог с GeoJSON файлами регионов.
                Если не указан, используется путь из конфигурации.
        """
        from app.config import regions_path

        self.regions_dir = regions_dir or regions_path

    def load_all_regions(self) -> gpd.GeoDataFrame:
        """Загрузить все GeoJSON файлы из каталога регионов.

        Returns:
            GeoDataFrame с объединёнными геометриями всех регионов.
        """
        gdf_data: list[gpd.GeoDataFrame] = []

        for region_json in self.regions_dir.iterdir():
            if region_json.suffix != ".geojson":
                continue

            gdf = load_and_validate_geojson_file(region_json)
            gdf_data.append(gdf)

        if not gdf_data:
            raise ValueError(
                f"В каталоге {self.regions_dir} не найдено ни одного .geojson файла",
            )

        # Объединяем GeoDataFrames напрямую через geopandas
        json_df = gpd.GeoDataFrame(pd.concat(gdf_data, ignore_index=True))
        json_df.dropna(inplace=True, axis=1)

        # Удаляем возможные дубликаты по названию региона, чтобы в результирующем
        # GeoDataFrame имена были уникальны
        json_df = gpd.GeoDataFrame(json_df.drop_duplicates(subset="name"))

        return json_df
