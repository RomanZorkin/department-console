import geopandas as gpd
from app.services.data_loader import create_gdf
from app.config import regions_path


def test_create_gdf_returns_geodataframe():
    gdf = create_gdf(regions_path)
    assert isinstance(gdf, gpd.GeoDataFrame)


def test_create_gdf_has_required_columns():
    gdf = create_gdf(regions_path)
    for col in ("name", "geometry", "value", "population", "area", "gdp"):
        assert col in gdf.columns


def test_create_gdf_geometry_not_empty():
    gdf = create_gdf(regions_path)
    # хотя бы одна валидная геометрия
    assert len(gdf) > 0
    assert gdf["geometry"].notna().all()


def test_create_gdf_name_unique_non_empty():
    gdf = create_gdf(regions_path)
    assert gdf["name"].notna().all()
    # в исходных geojson имена регионов должны быть хотя бы уникальны по строке
    assert gdf["name"].is_unique
