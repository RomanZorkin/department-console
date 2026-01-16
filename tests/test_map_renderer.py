import pydeck as pdk
from app.services.map_renderer import render_map
from app.services.data_loader import load_data


def test_render_map():
    gdf = load_data()
    deck = render_map(gdf)
    assert isinstance(deck, pdk.Deck)
    assert len(deck.layers) == 2  # Заливка и границы
