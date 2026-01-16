from pathlib import Path

import geopandas as gpd
import pandas as pd

from app.config import regions_path
from app.services.csv_loader import CSVLoader
from app.services.geojson_loader import GeoJSONLoader


class DataLoader:
    """Загрузчик и валидатор геоданных и данных организаций.

    Логика, ранее реализованная через набор функций, инкапсулирована в класс,
    чтобы упростить переиспользование и возможное расширение (другие
    источники данных, разные пути и т.п.).

    При инициализации загружает данные и сохраняет их как атрибуты:
    - csv_df: DataFrame с аналитическими данными из CSV
    - organizations_df: DataFrame с данными об организациях из CSV
    - geojson_df: GeoDataFrame с геометрией регионов из GeoJSON
    - gdf: GeoDataFrame с объединёнными геоданными и данными организаций
    """

    def __init__(self, regions_dir: Path | None = None) -> None:
        """Инициализация загрузчика данных.

        Args:
            regions_dir: Каталог с GeoJSON файлами регионов.
                Если не указан, используется путь из конфигурации.
        """
        self.regions_dir = regions_dir or regions_path
        self.csv_df: pd.DataFrame = CSVLoader.load_analytic_data()
        self.organizations_df: pd.DataFrame = CSVLoader.load_organizations_data()
        self.geojson_df: gpd.GeoDataFrame = self._load_geojson_data()
        self.gdf: gpd.GeoDataFrame = self._merge_data()

    def _load_geojson_data(self) -> gpd.GeoDataFrame:
        """Загрузить и обработать GeoJSON данные.

        Returns:
            GeoDataFrame с геометрией регионов из GeoJSON.
        """
        geojson_loader = GeoJSONLoader(regions_dir=self.regions_dir)
        return geojson_loader.load_all_regions()

    def _merge_data(self) -> gpd.GeoDataFrame:
        """Объединить GeoJSON и данные организаций.

        Мерджит данные по столбцам: 'name' (GeoJSON) == 'region' (organizations).

        Returns:
            GeoDataFrame с объединёнными данными.
        """
        merged = self.geojson_df.merge(
            self.organizations_df, left_on="name", right_on="region", how="left"
        )

        if not isinstance(merged, gpd.GeoDataFrame):
            merged = gpd.GeoDataFrame(merged, geometry=self.geojson_df.geometry)

        return merged
