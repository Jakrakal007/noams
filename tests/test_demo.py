import pytest
from demo.generate_demo_data import generate
from app.core.config import Settings


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_synthetic_pipeline_and_traceability(client, tmp_path, extension):
    folder = generate(tmp_path)
    def upload(name):
        filename = name + "." + extension
        response = client.post("/api/analysis/upload", files={"file": (filename, (folder/filename).read_bytes())})
        assert response.status_code == 200, response.text
        return response.json()
    history = upload("purchases_history_demo")
    assert history["valid_records"] == 3 and history["findings_summary"]["total"] == 0
    result = upload("purchases_demo")
    assert result["valid_records"] == 8 and result["invalid_records"] == 0
    assert result["findings_summary"]["total"] == 5
    assert {f["rule_code"] for f in result["findings"]} == {
        "DUPLICATE_PURCHASE", "UNUSUAL_SUPPLIER_AMOUNT", "BUDGET_DEVIATION",
        "UNAPPROVED_PURCHASE", "SPLIT_PURCHASE"}
    assert all(e["status"] == "completed" for e in result["rule_executions"])
    detail = client.get(f'/api/analysis/{result["analysis_id"]}').json()
    assert len(detail["transactions"]) == 8
    assert all(f["evidence_json"] for f in detail["findings"])
    assert all(e["configuration_snapshot_json"] is not None for e in detail["rule_executions"])
    for path in ("/", "/analysis", f'/analysis/{result["analysis_id"]}', "/rules", "/docs", "/api/health"):
        assert client.get(path).status_code == 200
    normal = upload("purchases_normal_demo")
    assert normal["findings_summary"]["total"] == 0
    invalid = upload("purchases_validation_demo")
    assert invalid["valid_records"] == 1 and invalid["invalid_records"] == 1 and invalid["errors"]


def test_demo_rejects_external_database_and_upload_directory(tmp_path):
    with pytest.raises(ValueError):
        Settings(database_url="sqlite:///external.db")
    with pytest.raises(ValueError):
        Settings(noams_upload_dir=tmp_path)
