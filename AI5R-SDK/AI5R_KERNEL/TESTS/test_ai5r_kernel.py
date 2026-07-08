from AI5R_KERNEL import AI5R


def test_ai5r_kernel_loads_product_and_runs_goal(tmp_path):
    ai5r = AI5R(root_path=tmp_path)

    loaded = ai5r.load("UMKM OS")

    assert loaded["status"] == "RUNNING"
    assert loaded["product"] == "UMKM_OS"

    result = ai5r.run("Create UMKM sales plan")

    assert result["status"] == "SUCCESS"
    assert result["product"] == "UMKM_OS"
    assert result["pipeline_id"].startswith("PIPE-CMD-")


def test_ai5r_kernel_use_and_ask(tmp_path):
    ai5r = AI5R(root_path=tmp_path)

    loaded = ai5r.use("UMKM OS")

    assert loaded["status"] == "RUNNING"

    result = ai5r.ask("Create marketing strategy")

    assert result["status"] == "SUCCESS"
    assert result["pipeline_id"].startswith("PIPE-CMD-")
