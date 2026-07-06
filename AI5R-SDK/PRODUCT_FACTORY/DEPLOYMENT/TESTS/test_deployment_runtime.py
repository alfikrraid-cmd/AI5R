from PRODUCT_FACTORY.DEPLOYMENT import (
    DeploymentRuntime,
)



def test_product_deployment():


    runtime = DeploymentRuntime()


    result = runtime.deploy(

        "UMKM-AI-001",

        "1.0.0"

    )


    assert result["status"] == "DEPLOYED"


    assert runtime.status(
        "UMKM-AI-001"
    ) == "ACTIVE"
