from BUSINESS_VERTICALS.REGISTRY import VerticalRegistry


def test_vertical_registry():
    registry = VerticalRegistry()

    assert "UMKM_OS" in registry.names()
    assert "SCHOOL_OS" in registry.names()
    assert "AUDITOR_OS" in registry.names()

    runtime = registry.create("UMKM_OS")

    assert runtime.__class__.__name__ == "AI5RUMKMOSRuntime"
