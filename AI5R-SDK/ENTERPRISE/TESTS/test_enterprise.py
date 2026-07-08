from ENTERPRISE import EnterpriseRegistry


def test_enterprise_registry_creates_company_objects():
    registry = EnterpriseRegistry()

    company = registry.register(
        object_type="company",
        name="PT Mitra Andalan Servisindo",
    )

    assert company.object_id.startswith("COM-")
    assert company.object_type == "company"
    assert company.name == "PT Mitra Andalan Servisindo"
