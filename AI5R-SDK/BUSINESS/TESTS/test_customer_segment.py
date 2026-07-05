import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BUSINESS.customer_segment import CustomerSegment


def test_customer_segment():

    segment = CustomerSegment(
        segment_code="SME",
        segment_name="Small Medium Enterprise",
        description="Businesses that need digital workers without hiring full teams",
        target_industry="General Business",
        company_size="1-50",
        primary_need="Affordable digital workforce",
        buying_trigger="Need to scale operations without increasing headcount",
    )

    assert segment.object_type == "CUSTOMER_SEGMENT"
    assert segment.status == "ACTIVE"
    assert segment.segment_code == "SME"
    assert segment.segment_name == "Small Medium Enterprise"
    assert segment.segment_id.startswith("SEG-")
