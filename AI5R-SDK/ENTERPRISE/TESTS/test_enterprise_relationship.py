from ENTERPRISE import EnterpriseRegistry, EnterpriseRelationshipGraph


def test_enterprise_relationship_graph_connects_enterprise_to_company():
    registry = EnterpriseRegistry()
    graph = EnterpriseRelationshipGraph()

    holding = registry.register("enterprise", "Alfikr Group")
    company = registry.register("company", "PT Mitra Andalan Servisindo")

    relationship = graph.connect(
        source_id=holding.object_id,
        target_id=company.object_id,
        relationship_type="OWNS",
    )

    assert relationship.relationship_type == "OWNS"
    assert graph.children_of(holding.object_id)[0].target_id == company.object_id
    assert graph.parents_of(company.object_id)[0].source_id == holding.object_id
