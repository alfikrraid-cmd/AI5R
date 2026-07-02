import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from manifest_loader import ManifestLoader
from GENERATORS.sql_generator import SQLGenerator


def test_sql_generator():
    manifest_path = Path("PRODUCTS/LTSA-BRAIN/product.manifest.json")
    output_path = Path("PRODUCTS/LTSA-BRAIN/RELEASE/database.sql")

    loader = ManifestLoader()
    unit = loader.load(str(manifest_path))

    generator = SQLGenerator()
    sql = generator.generate(unit, str(output_path))

    assert output_path.exists()
    assert "CREATE TABLE IF NOT EXISTS ltsa_customers" in sql
    assert "CREATE TABLE IF NOT EXISTS ltsa_pumps" in sql
    assert "CREATE TABLE IF NOT EXISTS ltsa_assets" in sql
    assert "CREATE TABLE IF NOT EXISTS ltsa_inspections" in sql
    assert "CREATE TABLE IF NOT EXISTS ltsa_maintenances" in sql

    print("FM-100.3.1 SQL Generator OK")


if __name__ == "__main__":
    test_sql_generator()
