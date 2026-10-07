from io import BytesIO
from datetime import date
from decimal import Decimal

from openpyxl import Workbook
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.models import AnalysisRun, Finding, RuleExecution, Transaction
from app.main import app
from app.validators.analysis import REQUIRED_COLUMNS, validate_row


VALID_ROW = {
    "transaction_id": "TX-001",
    "transaction_date": "2026-07-16",
    "supplier_name": "Proveedor Uno",
    "department": "Operaciones",
    "category": "Insumos",
    "quantity": "2",
    "unit_price": "15.50",
    "total_amount": "31.00",
    "approval_status": "approved",
    "purchase_order": "PO-001",
}


def csv_content(*rows: dict[str, str], columns=REQUIRED_COLUMNS) -> bytes:
    lines = [",".join(columns)]
    lines.extend(",".join(str(row.get(column, "")) for column in columns) for row in rows)
    return "\n".join(lines).encode("utf-8")


def xlsx_content(*rows: dict[str, str]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(REQUIRED_COLUMNS)
    for row in rows:
        sheet.append([row.get(column) for column in REQUIRED_COLUMNS])
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def test_valid_record() -> None:
    assert validate_row(VALID_ROW, 2) == []


def test_invalid_record_reports_each_field() -> None:
    invalid = VALID_ROW | {
        "supplier_name": "",
        "transaction_date": "not-a-date",
        "quantity": 0,
        "total_amount": -1,
    }

    errors = validate_row(invalid, 18)

    assert {error.column for error in errors} == {
        "supplier_name",
        "transaction_date",
        "quantity",
        "total_amount",
    }
    assert all(error.row == 18 for error in errors)


def test_upload_valid_csv(client) -> None:
    response = client.post(
        "/api/analysis/upload",
        files={"file": ("compras.csv", csv_content(VALID_ROW), "text/csv")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["analysis_id"] == 1
    assert result["status"] == "completed"
    assert result["total_records"] == 1
    assert result["valid_records"] == 1
    assert result["invalid_records"] == 0
    assert result["errors"] == []


def test_upload_empty_file(client) -> None:
    response = client.post(
        "/api/analysis/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_file"


def test_upload_requires_file(client) -> None:
    response = client.post("/api/analysis/upload")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "file_required"


def test_upload_invalid_extension(client) -> None:
    response = client.post(
        "/api/analysis/upload",
        files={"file": ("compras.txt", b"content", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_extension"


def test_upload_missing_columns(client) -> None:
    columns = tuple(column for column in REQUIRED_COLUMNS if column != "supplier_name")
    response = client.post(
        "/api/analysis/upload",
        files={"file": ("compras.csv", csv_content(VALID_ROW, columns=columns), "text/csv")},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_columns"
    assert "supplier_name" in error["message"]


def test_invalid_xlsx_returns_controlled_error(client) -> None:
    response = client.post(
        "/api/analysis/upload",
        files={
            "file": (
                "corrupto.xlsx",
                b"not an excel workbook",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "xlsx_read_error", "message": "The Excel file could not be read."}
    }


def test_upload_xlsx_returns_invalid_row_details(client) -> None:
    invalid = VALID_ROW | {"supplier_name": "", "total_amount": -4}
    response = client.post(
        "/api/analysis/upload",
        files={
            "file": (
                "compras_julio.xlsx",
                xlsx_content(VALID_ROW, invalid),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["filename"] == "compras_julio.xlsx"
    assert result["total_records"] == 2
    assert result["valid_records"] == 1
    assert result["invalid_records"] == 1
    assert result["processing_time_ms"] >= 1
    assert result["errors"] == [
        {"row": 3, "column": "supplier_name", "message": "Value is required"},
        {"row": 3, "column": "total_amount", "message": "Amount cannot be negative"},
    ]


def test_dashboard_reads_saved_execution(client) -> None:
    client.post(
        "/api/analysis/upload",
        files={"file": ("compras.csv", csv_content(VALID_ROW), "text/csv")},
    )

    response = client.get("/")

    assert response.status_code == 200
    assert '<strong id="analyses-count">1</strong>' in response.text
    assert '<strong id="records-processed">1</strong>' in response.text


def test_upload_with_findings_persists_transactions_and_rules(client) -> None:
    columns = REQUIRED_COLUMNS + ("budget_amount", "currency")
    rows = [
        VALID_ROW | {"transaction_id": "TX-1", "total_amount": "4200", "purchase_order": "PO-DUP", "budget_amount": "5000", "currency": "PEN"},
        VALID_ROW | {"transaction_id": "TX-2", "total_amount": "4200", "purchase_order": "PO-DUP", "budget_amount": "5000", "currency": "PEN"},
        VALID_ROW | {"transaction_id": "TX-3", "total_amount": "6000", "purchase_order": "PO-3", "approval_status": "pending", "budget_amount": "5000", "currency": "PEN"},
    ]
    response = client.post(
        "/api/analysis/upload",
        files={"file": ("findings.csv", csv_content(*rows, columns=columns), "text/csv")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed_with_findings"
    assert result["findings_summary"]["total"] >= 3
    assert {item["rule_code"] for item in result["findings"]} >= {
        "DUPLICATE_PURCHASE",
        "BUDGET_DEVIATION",
        "UNAPPROVED_PURCHASE",
    }
    assert len(result["rule_executions"]) == 5
    assert all(item["status"] == "completed" for item in result["rule_executions"])

    detail = client.get(f"/api/analysis/{result['analysis_id']}")
    assert detail.status_code == 200
    assert len(detail.json()["transactions"]) == 3
    assert detail.json()["findings_summary"]["total"] == result["findings_summary"]["total"]


def test_invalid_rows_are_not_persisted_or_evaluated(client) -> None:
    invalid = VALID_ROW | {"transaction_id": "TX-BAD", "quantity": "0", "approval_status": "pending"}
    response = client.post(
        "/api/analysis/upload",
        files={"file": ("quality.csv", csv_content(VALID_ROW, invalid), "text/csv")},
    )
    result = response.json()
    detail = client.get(f"/api/analysis/{result['analysis_id']}").json()
    assert result["invalid_records"] == 1
    assert len(detail["transactions"]) == 1
    assert all(item["rule_code"] != "UNAPPROVED_PURCHASE" for item in detail["findings"])


def test_findings_endpoints_filter_paginate_and_return_detail(client) -> None:
    row = VALID_ROW | {"approval_status": "rejected", "total_amount": "12000"}
    upload = client.post(
        "/api/analysis/upload",
        files={"file": ("risk.csv", csv_content(row), "text/csv")},
    ).json()
    finding_id = next(
        item["id"] for item in upload["findings"] if item["rule_code"] == "UNAPPROVED_PURCHASE"
    )

    listing = client.get(
        "/api/findings",
        params={"analysis_id": upload["analysis_id"], "severity": "critical", "page_size": 1},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1
    assert listing.json()["page_size"] == 1

    detail = client.get(f"/api/findings/{finding_id}")
    assert detail.status_code == 200
    assert detail.json()["supplier_name"] == "Proveedor Uno"
    assert detail.json()["evidence_json"]["approval_status"] == "rejected"


def test_not_found_responses_are_controlled(client) -> None:
    analysis = client.get("/api/analysis/999")
    finding = client.get("/api/findings/999")
    assert analysis.status_code == 404
    assert analysis.json()["error"]["code"] == "analysis_not_found"
    assert finding.status_code == 404
    assert finding.json()["error"]["code"] == "finding_not_found"


def test_dashboard_metrics_are_database_backed(client) -> None:
    row = VALID_ROW | {"approval_status": "rejected", "total_amount": "12000"}
    client.post(
        "/api/analysis/upload",
        files={"file": ("metrics.csv", csv_content(row), "text/csv")},
    )
    response = client.get("/api/analysis/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["analyses_count"] == 1
    assert metrics["records_processed"] == 1
    assert metrics["findings_count"] >= 1
    assert metrics["critical_risks"] >= 1
    assert Decimal(metrics["estimated_impact"]) == Decimal("12000.00")


def test_uploaded_file_is_stored_with_safe_unique_name(client) -> None:
    response = client.post(
        "/api/analysis/upload",
        files={"file": ("../quarterly purchases.csv", csv_content(VALID_ROW), "text/csv")},
    )

    assert response.status_code == 200
    stored = list(settings.noams_upload_dir.iterdir())
    assert len(stored) == 1
    assert stored[0].parent == settings.noams_upload_dir
    assert stored[0].name.endswith("_quarterly_purchases.csv")
    assert stored[0].read_bytes() == csv_content(VALID_ROW)
    assert not (settings.noams_upload_dir.parent / "quarterly purchases.csv").exists()


def test_analysis_history_is_newest_first_and_supports_pagination(client) -> None:
    first = client.post(
        "/api/analysis/upload",
        files={"file": ("first.csv", csv_content(VALID_ROW), "text/csv")},
    ).json()
    second = client.post(
        "/api/analysis/upload",
        files={"file": ("second.csv", csv_content(VALID_ROW), "text/csv")},
    ).json()

    history = client.get("/api/analysis", params={"limit": 1, "offset": 0})
    next_page = client.get("/api/analysis", params={"limit": 1, "offset": 1})

    assert history.status_code == 200
    assert [item["id"] for item in history.json()] == [second["analysis_id"]]
    assert [item["id"] for item in next_page.json()] == [first["analysis_id"]]


def test_analysis_history_groups_exact_filenames_and_uses_latest_run(client) -> None:
    single = client.post(
        "/api/analysis/upload",
        files={"file": ("single.csv", csv_content(VALID_ROW), "text/csv")},
    ).json()
    versions = []
    for count in (1, 2, 3):
        rows = [VALID_ROW | {"transaction_id": f"TX-{count}-{index}"} for index in range(count)]
        versions.append(
            client.post(
                "/api/analysis/upload",
                files={"file": ("repeated.csv", csv_content(*rows), "text/csv")},
            ).json()
        )

    history = client.get("/api/analysis").json()
    repeated = next(item for item in history if item["filename"] == "repeated.csv")
    unchanged = next(item for item in history if item["filename"] == "single.csv")

    assert len(history) == 2
    assert repeated["id"] == versions[-1]["analysis_id"]
    assert repeated["total_records"] == 3
    assert repeated["versions_count"] == 3
    assert repeated["is_updated"] is True
    assert unchanged["id"] == single["analysis_id"]
    assert unchanged["versions_count"] == 1
    assert unchanged["is_updated"] is False
    assert [item["filename"] for item in history] == ["repeated.csv", "single.csv"]

    with client.test_session_factory() as db:
        stored_runs = db.query(AnalysisRun).filter_by(filename="repeated.csv").all()
        assert len(stored_runs) == 3
        assert (
            db.query(Transaction)
            .filter(Transaction.analysis_run_id.in_([run.id for run in stored_runs]))
            .count()
            == 6
        )


def test_grouped_history_filters_the_latest_version_without_showing_older_matches(client) -> None:
    older = client.post(
        "/api/analysis/upload",
        files={"file": ("filtered.csv", csv_content(VALID_ROW), "text/csv")},
    ).json()
    latest = client.post(
        "/api/analysis/upload",
        files={"file": ("filtered.csv", csv_content(VALID_ROW), "text/csv")},
    ).json()
    with client.test_session_factory() as db:
        db.get(AnalysisRun, older["analysis_id"]).status = "failed"
        db.get(AnalysisRun, latest["analysis_id"]).status = "completed"
        db.commit()

    matching = client.get(
        "/api/analysis", params={"filename": "filter", "status": "completed"}
    ).json()
    older_status = client.get(
        "/api/analysis", params={"filename": "filter", "status": "failed"}
    ).json()

    assert [item["id"] for item in matching] == [latest["analysis_id"]]
    assert matching[0]["versions_count"] == 2
    assert older_status == []


def test_deleting_latest_grouped_version_reveals_previous_and_updates_flag(client) -> None:
    versions = [
        client.post(
            "/api/analysis/upload",
            files={"file": ("versions.csv", csv_content(VALID_ROW), "text/csv")},
        ).json()["analysis_id"]
        for _ in range(3)
    ]

    assert client.delete(f"/api/analysis/{versions[2]}").status_code == 204
    after_first_delete = client.get("/api/analysis").json()
    assert len(after_first_delete) == 1
    assert after_first_delete[0]["id"] == versions[1]
    assert after_first_delete[0]["versions_count"] == 2
    assert after_first_delete[0]["is_updated"] is True

    assert client.delete(f"/api/analysis/{versions[1]}").status_code == 204
    after_second_delete = client.get("/api/analysis").json()
    assert len(after_second_delete) == 1
    assert after_second_delete[0]["id"] == versions[0]
    assert after_second_delete[0]["versions_count"] == 1
    assert after_second_delete[0]["is_updated"] is False


def test_persisted_analysis_is_available_to_another_test_client(client) -> None:
    upload = client.post(
        "/api/analysis/upload",
        files={"file": ("persistent.csv", csv_content(VALID_ROW), "text/csv")},
    ).json()

    with TestClient(app) as second_client:
        response = second_client.get(f"/api/analysis/{upload['analysis_id']}")

    assert response.status_code == 200
    assert response.json()["filename"] == "persistent.csv"


def test_analysis_detail_restores_findings_executions_and_validation_errors(client) -> None:
    invalid = VALID_ROW | {"transaction_id": "TX-BAD", "quantity": "0"}
    finding_row = VALID_ROW | {
        "transaction_id": "TX-RISK",
        "approval_status": "rejected",
        "total_amount": "12000",
    }
    upload = client.post(
        "/api/analysis/upload",
        files={"file": ("detail.csv", csv_content(finding_row, invalid), "text/csv")},
    ).json()

    detail = client.get(f"/api/analysis/{upload['analysis_id']}")

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["errors"] == [
        {"row": 3, "column": "quantity", "message": "Must be greater than zero"}
    ]
    assert any(item["rule_code"] == "UNAPPROVED_PURCHASE" for item in payload["findings"])
    assert len(payload["rule_executions"]) == 5


def test_failed_upload_does_not_leave_an_orphan_file(client) -> None:
    response = client.post(
        "/api/analysis/upload",
        files={"file": ("broken.xlsx", b"not a workbook", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 400
    assert not settings.noams_upload_dir.exists() or list(settings.noams_upload_dir.iterdir()) == []


def test_analysis_history_and_detail_pages_use_persisted_data(client) -> None:
    upload = client.post(
        "/api/analysis/upload",
        files={"file": ("page-history.csv", csv_content(VALID_ROW), "text/csv")},
    ).json()

    history_page = client.get("/analysis")
    detail_page = client.get(f"/analysis/{upload['analysis_id']}")

    assert history_page.status_code == 200
    assert "page-history.csv" in history_page.text
    assert f'/analysis/{upload["analysis_id"]}' in history_page.text
    assert detail_page.status_code == 200
    assert "Run Summary" in detail_page.text
    assert "page-history.csv" in detail_page.text


def test_unknown_analysis_page_returns_404(client) -> None:
    response = client.get("/analysis/999")

    assert response.status_code == 404


def test_delete_analysis_removes_only_target_run_and_associated_data(client) -> None:
    risk_row = VALID_ROW | {
        "transaction_id": "TX-DELETE",
        "approval_status": "rejected",
        "total_amount": "12000",
    }
    target = client.post(
        "/api/analysis/upload",
        files={"file": ("delete-me.csv", csv_content(risk_row), "text/csv")},
    ).json()
    survivor = client.post(
        "/api/analysis/upload",
        files={"file": ("keep-me.csv", csv_content(VALID_ROW), "text/csv")},
    ).json()
    target_id = target["analysis_id"]
    survivor_id = survivor["analysis_id"]

    with client.test_session_factory() as db:
        assert db.query(Transaction).filter_by(analysis_run_id=target_id).count() == 1
        assert db.query(Finding).filter_by(analysis_run_id=target_id).count() >= 1
        assert db.query(RuleExecution).filter_by(analysis_run_id=target_id).count() == 5

    response = client.delete(f"/api/analysis/{target_id}")

    assert response.status_code == 204
    with client.test_session_factory() as db:
        assert db.get(AnalysisRun, target_id) is None
        assert db.query(Transaction).filter_by(analysis_run_id=target_id).count() == 0
        assert db.query(Finding).filter_by(analysis_run_id=target_id).count() == 0
        assert db.query(RuleExecution).filter_by(analysis_run_id=target_id).count() == 0
        assert db.get(AnalysisRun, survivor_id) is not None

    metrics = client.get("/api/analysis/metrics").json()
    assert metrics["analyses_count"] == 1
    assert metrics["records_processed"] == 1
    assert client.get(f"/api/analysis/{survivor_id}").status_code == 200


def test_delete_unknown_analysis_returns_404(client) -> None:
    response = client.delete("/api/analysis/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_not_found"


def test_delete_analysis_handles_each_child_record_combination(client) -> None:
    def add_transaction(db, run_id: int) -> None:
        db.add(
            Transaction(
                analysis_run_id=run_id,
                transaction_id=f"TX-{run_id}",
                transaction_date=date(2026, 8, 6),
                supplier_name="Deletion Test Supplier",
                department="Operations",
                category="Testing",
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
                total_amount=Decimal("100"),
                approval_status="approved",
                source_row_number=2,
            )
        )

    def add_finding(db, run_id: int) -> None:
        db.add(
            Finding(
                analysis_run_id=run_id,
                rule_code="DELETE_TEST",
                title="Deletion test finding",
                description="Finding created to verify analysis deletion.",
                category="testing",
                severity="low",
            )
        )

    def add_execution(db, run_id: int) -> None:
        db.add(
            RuleExecution(
                analysis_run_id=run_id,
                rule_code="DELETE_TEST",
                rule_name="Deletion Test Rule",
                status="completed",
            )
        )

    with client.test_session_factory() as db:
        runs = {}
        for scenario in ("transactions", "findings", "executions", "all"):
            run = AnalysisRun(filename=f"{scenario}.csv", status="completed")
            db.add(run)
            db.flush()
            runs[scenario] = run.id
            if scenario in {"transactions", "all"}:
                add_transaction(db, run.id)
            if scenario in {"findings", "all"}:
                add_finding(db, run.id)
            if scenario in {"executions", "all"}:
                add_execution(db, run.id)
        survivor = AnalysisRun(filename="survivor.csv", status="completed")
        db.add(survivor)
        db.commit()
        survivor_id = survivor.id

    for run_id in runs.values():
        assert client.delete(f"/api/analysis/{run_id}").status_code == 204

    with client.test_session_factory() as db:
        assert all(db.get(AnalysisRun, run_id) is None for run_id in runs.values())
        assert db.query(Transaction).filter(Transaction.analysis_run_id.in_(runs.values())).count() == 0
        assert db.query(Finding).filter(Finding.analysis_run_id.in_(runs.values())).count() == 0
        assert db.query(RuleExecution).filter(RuleExecution.analysis_run_id.in_(runs.values())).count() == 0
        assert db.get(AnalysisRun, survivor_id) is not None
