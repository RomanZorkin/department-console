import geopandas as gpd
import pandas as pd
from pathlib import Path

from app.services.data_loader import DataLoader
from app.services.csv_loader import CSVLoader
from app.config import regions_path


# ============================================================================
# Тесты для DataLoader
# ============================================================================


def test_create_gdf_returns_geodataframe():
    """Проверка, что DataLoader.gdf возвращает GeoDataFrame."""
    loader = DataLoader(regions_dir=regions_path)
    gdf = loader.gdf
    assert isinstance(gdf, gpd.GeoDataFrame)


def test_create_gdf_has_required_columns():
    """Проверка наличия обязательных колонок в GeoDataFrame."""
    loader = DataLoader(regions_dir=regions_path)
    gdf = loader.gdf
    # Обязательные колонки из GeoJSON
    assert "name" in gdf.columns
    assert "geometry" in gdf.columns
    # Колонки из CSV (могут быть NaN для регионов без данных)
    assert "region" in gdf.columns or "value" in gdf.columns


def test_create_gdf_geometry_not_empty():
    """Проверка, что геометрия не пустая."""
    loader = DataLoader(regions_dir=regions_path)
    gdf = loader.gdf
    # хотя бы одна валидная геометрия
    assert len(gdf) > 0
    assert gdf["geometry"].notna().all()


def test_create_gdf_name_not_empty():
    """Проверка, что имена регионов не пустые."""
    loader = DataLoader(regions_dir=regions_path)
    gdf = loader.gdf
    assert gdf["name"].notna().all()
    assert len(gdf) > 0


def test_data_loader_class():
    """Проверка работы класса DataLoader."""
    loader = DataLoader(regions_dir=regions_path)
    gdf = loader.gdf
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) > 0


def test_data_loader_attributes():
    """Проверка наличия атрибутов с загруженными данными."""
    loader = DataLoader(regions_dir=regions_path)
    
    # Проверяем наличие атрибутов
    assert hasattr(loader, "csv_df"), "Атрибут csv_df должен быть доступен"
    assert hasattr(loader, "geojson_df"), "Атрибут geojson_df должен быть доступен"
    assert hasattr(loader, "gdf"), "Атрибут gdf должен быть доступен"
    
    # Проверяем типы
    assert isinstance(loader.csv_df, pd.DataFrame), "csv_df должен быть DataFrame"
    assert isinstance(loader.geojson_df, gpd.GeoDataFrame), "geojson_df должен быть GeoDataFrame"
    assert isinstance(loader.gdf, gpd.GeoDataFrame), "gdf должен быть GeoDataFrame"
    
    # Проверяем, что данные загружены
    assert len(loader.csv_df) > 0, "csv_df не должен быть пустым"
    assert len(loader.geojson_df) > 0, "geojson_df не должен быть пустым"
    assert len(loader.gdf) > 0, "gdf не должен быть пустым"
    
    # Проверяем, что gdf содержит данные из обоих источников
    assert "name" in loader.gdf.columns, "gdf должен содержать колонку 'name'"
    assert "region" in loader.gdf.columns, "gdf должен содержать колонку 'region'"


def test_load_data_function():
    """Проверка загрузки данных через DataLoader по умолчанию."""
    loader = DataLoader()
    gdf = loader.gdf
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) > 0


def test_create_gdf_merge_geojson_csv():
    """Проверка корректности merge между GeoJSON (name) и CSV (region)."""
    loader = DataLoader(regions_dir=regions_path)
    gdf = loader.gdf
    
    # Проверяем, что колонки из обоих источников присутствуют
    assert "name" in gdf.columns, "Колонка 'name' из GeoJSON должна присутствовать"
    assert "region" in gdf.columns, "Колонка 'region' из CSV должна присутствовать"
    
    # Проверяем, что есть хотя бы некоторые совпадения
    # (не все регионы могут иметь данные в CSV)
    regions_with_data = gdf[gdf["region"].notna()]
    assert len(regions_with_data) > 0, "Должен быть хотя бы один регион с данными из CSV"
    
    # Проверяем, что для регионов с данными name == region
    for idx, row in regions_with_data.iterrows():
        assert row["name"] == row["region"], (
            f"Несоответствие: name='{row['name']}' != region='{row['region']}'"
        )


# ============================================================================
# Тесты для CSVLoader
# ============================================================================


def test_csv_loader_load_analytic_data():
    """Проверка загрузки аналитических данных через CSVLoader."""
    csv_loader = CSVLoader()
    df = csv_loader.load_analytic_data()
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    # Проверяем наличие обязательных колонок из AnalyticRecord
    required_cols = ["region_name", "region", "value", "percent_change", 
                     "budget_millions", "population_change", "details"]
    for col in required_cols:
        assert col in df.columns, f"Колонка {col} отсутствует"


def test_csv_loader_load_organizations_data():
    """Проверка загрузки данных об организациях через CSVLoader."""
    csv_loader = CSVLoader()
    df = csv_loader.load_organizations_data()
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    # Проверяем наличие обязательных колонок из OrganizationRecord
    required_cols = ["city", "region", "by_staff", "by_list", "buget_limits",
                     "cash_execution", "equipment", "faulty_equipment"]
    for col in required_cols:
        assert col in df.columns, f"Колонка {col} отсутствует"


def test_csv_loader_load_analytic_data_with_path():
    """Проверка загрузки аналитических данных с указанием пути."""
    csv_loader = CSVLoader()
    data_path = Path(__file__).resolve().parent.parent / "app" / "data" / "analytic" / "data.csv"
    df = csv_loader.load_analytic_data(path=data_path)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_csv_loader_load_csv_universal():
    """Проверка универсального метода load_csv."""
    from app.models import AnalyticRecord
    
    csv_loader = CSVLoader()
    data_path = Path(__file__).resolve().parent.parent / "app" / "data" / "analytic" / "data.csv"
    df = csv_loader.load_csv(path=data_path, model=AnalyticRecord)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "region" in df.columns
