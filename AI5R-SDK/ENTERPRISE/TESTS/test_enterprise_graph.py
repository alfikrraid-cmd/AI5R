from ENTERPRISE import EnterpriseRegistry
from ENTERPRISE.enterprise_graph import EnterpriseKnowledgeGraph


def test_enterprise_knowledge_graph_connects_enterprise_company_project():
    registry = EnterpriseRegistry()
    graph = EnterpriseKnowledgeGraph()

    enterprise = registry.register("enterprise", "Alfikr Group")
    company = registry.register("company", "PT Mitra Andalan Servisindo")
    project = registry.register("project", "PLTU Suralaya")

    graph.add_node(enterprise)
    graph.add_node(company)
    graph.add_node(project)

    graph.add_relationship(
        source_id=enterprise.object_id,
        target_id=company.object_id,
        relationship_type="OWNS",
    )

    graph.add_relationship(
        source_id=company.object_id,
        target_id=project.object_id,
        relationship_type="HAS_PROJECT",
    )

    assert graph.children(enterprise.object_id)[0].name == "PT Mitra Andalan Servisindo"
    assert graph.children(company.object_id)[0].name == "PLTU Suralaya"
    assert graph.parents(project.object_id)[0].name == "PT Mitra Andalan Servisindo"
    assert graph.neighbors(company.object_id)[0].name == "Alfikr Group"
    assert graph.find(project.object_id).name == "PLTU Suralaya"
    assert graph.find_by_type("company")[0].name == "PT Mitra Andalan Servisindo"
    assert graph.find_relationships("OWNS")[0].target_id == company.object_id
