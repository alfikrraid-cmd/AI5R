from {{ module_name }} import {{ class_name }}


def test_{{ module_name }}_object():
    obj = {{ class_name }}("obj-001", "Generated Object")

    assert obj.object_id == "obj-001"
    assert obj.name == "Generated Object"
    assert obj.to_dict()["object_id"] == "obj-001"
