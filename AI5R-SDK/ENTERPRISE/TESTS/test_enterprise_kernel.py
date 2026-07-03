import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ENTERPRISE.enterprise_kernel import EnterpriseKernel


def test_enterprise_kernel():
    kernel = EnterpriseKernel()

    kernel.register_unit("DF", "Digital Factory")
    kernel.register_unit("KF", "Knowledge Factory")
    kernel.register_unit("CF", "Capability Factory")

    status = kernel.status()

    assert status["name"] == "AI5R Digital Enterprise"
    assert status["version"] == "2.0.0"
    assert status["foundation_status"] == "FM-001 to FM-105 Frozen LTS"
    assert status["enterprise_units"]["DF"] == "Digital Factory"
    assert status["enterprise_units"]["KF"] == "Knowledge Factory"
    assert status["enterprise_units"]["CF"] == "Capability Factory"

    print("EL-001 Enterprise Kernel OK")


if __name__ == "__main__":
    test_enterprise_kernel()
