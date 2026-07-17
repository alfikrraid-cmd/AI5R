from FACTORY.CORE.universal_manufacturing_contract import (
    UNIVERSAL_MANUFACTURING_CONTRACT,
    stages_pending_implementation,
)


def test_contract_has_nine_stages_in_order():
    assert len(UNIVERSAL_MANUFACTURING_CONTRACT) == 9

    for index, stage in enumerate(UNIVERSAL_MANUFACTURING_CONTRACT, start=1):
        assert stage.order == index


def test_identity_and_relationship_resolution_are_the_only_interface_stages():
    pending = stages_pending_implementation()
    pending_names = {stage.name for stage in pending}

    assert pending_names == {"Identity Resolution", "Relationship Resolution"}


def test_all_other_stages_are_implemented():
    implemented = [
        stage for stage in UNIVERSAL_MANUFACTURING_CONTRACT if stage.status == "IMPLEMENTED"
    ]

    assert len(implemented) == 7
