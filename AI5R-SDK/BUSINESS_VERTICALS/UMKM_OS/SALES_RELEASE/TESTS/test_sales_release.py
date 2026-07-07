from BUSINESS_VERTICALS.UMKM_OS.SALES_RELEASE import (
    create_sales_release,
)



def test_sales_release():


    release = create_sales_release()


    assert release.name == "AI5R UMKM OS SALES DEMO"


    assert release.version == "1.0.0"


    assert release.status == "READY"


    assert len(
        release.demo_features
    ) == 6
