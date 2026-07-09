from ARCHITECTURE.canonical_factory_map import (
    CANONICAL_FACTORY_MAP,
    get_canonical,
    list_components_needing_confirmation,
)


def test_factory_map_has_required_components():
    assert "manufacturing_order" in CANONICAL_FACTORY_MAP
    assert "manufacturing_engine" in CANONICAL_FACTORY_MAP
    assert "base_manufacturing_station" in CANONICAL_FACTORY_MAP
    assert "station_registry" in CANONICAL_FACTORY_MAP


def test_base_station_canonical_is_active():
    assert get_canonical("base_manufacturing_station") == "FACTORY.CORE.manufacturing_station"
    assert CANONICAL_FACTORY_MAP["base_manufacturing_station"]["status"] == "ACTIVE"


def test_duplicate_areas_are_marked_for_review():
    pending = list_components_needing_confirmation()

    assert "manufacturing_engine" in pending
    assert "station_registry" in pending


def test_unknown_component_fails_fast():
    try:
        get_canonical("unknown_component")
    except KeyError as exc:
        assert "Unknown factory component" in str(exc)
    else:
        raise AssertionError("Expected unknown component lookup to fail")
