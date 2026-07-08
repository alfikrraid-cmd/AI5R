from ENTERPRISE import EnterpriseRegistry


def test_enterprise_registry_lists_objects_by_type():
    registry = EnterpriseRegistry()

    registry.register("company", "PT Mitra Andalan Servisindo")
    registry.register("company", "CV Razzan Teknik Mandiri")
    registry.register("brand", "Alleira Florist")

    companies = registry.list_by_type("company")
    brands = registry.list_by_type("brand")

    assert len(companies) == 2
    assert len(brands) == 1
    assert brands[0].name == "Alleira Florist"
