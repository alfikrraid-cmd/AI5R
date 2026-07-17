from models import ExtractionResult, FieldValue


def test_extraction_result_round_trips_through_dict():
    result = ExtractionResult(
        document_type="PUMP_DATASHEET",
        document_type_confidence=0.91,
        fields={
            "pump_manufacturer": FieldValue(value="ACME", confidence=0.95),
            "pump_model": FieldValue(value=None, confidence=None),
        },
        ocr_text="ACME PUMP CO. MODEL X-100",
        provider="claude",
    )

    round_tripped = ExtractionResult.from_dict(result.to_dict())

    assert round_tripped == result


def test_field_value_to_dict_preserves_none():
    fv = FieldValue(value=None, confidence=None)
    assert fv.to_dict() == {"value": None, "confidence": None}
