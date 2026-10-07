"""Generate independent, wholly fictional CSV/XLSX purchase examples."""
from pathlib import Path
import csv
from datetime import datetime
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ("transaction_id", "transaction_date", "supplier_name", "department",
           "category", "quantity", "unit_price", "total_amount", "approval_status",
           "purchase_order", "budget_amount", "currency")


def purchase(code, supplier, amount, day="2026-01-15", status="approved", budget="", order=None):
    return dict(zip(COLUMNS, (code, day, supplier, "Demo Operations", "Demo Materials",
                            "1", str(amount), str(amount), status, order or "DEMO-PO-"+code,
                            str(budget), "PEN")))


def datasets():
    baseline = [purchase("HIST-"+str(i), "FICTIONAL-DEMO-ORBIT-001", amount,
                         day=f"2026-01-{i*5:02d}")
                for i, amount in enumerate((900, 1000, 1100), start=1)]
    normal = [purchase("NORMAL-001", "FICTIONAL-DEMO-CLOUD-002", 320)]
    cases = [
        purchase("DUP-001", "FICTIONAL-DEMO-PRISM-003", 800, order="DEMO-DUP-PO"),
        purchase("DUP-002", "FICTIONAL-DEMO-PRISM-003", 800, order="DEMO-DUP-PO"),
        purchase("UNUSUAL-001", "FICTIONAL-DEMO-ORBIT-001", 5000),
        purchase("BUDGET-001", "FICTIONAL-DEMO-CUBE-004", 1500, budget=1000),
        purchase("APPROVAL-001", "FICTIONAL-DEMO-LUMEN-005", 12000, status="rejected"),
        purchase("SPLIT-001", "FICTIONAL-DEMO-ARC-006", 2600, day="2026-01-20"),
        purchase("SPLIT-002", "FICTIONAL-DEMO-ARC-006", 2500, day="2026-01-22"),
        *normal,
    ]
    invalid = [purchase("VALID-001", "FICTIONAL-DEMO-FLUX-007", 75),
               purchase("INVALID-001", "FICTIONAL-DEMO-FLUX-007", -20, day="invalid-date")]
    invalid[1]["quantity"] = "0"
    return {"purchases_history_demo": baseline, "purchases_demo": cases,
            "purchases_normal_demo": normal, "purchases_validation_demo": invalid}


def generate(output=None):
    output = Path(output) if output is not None else ROOT / "demo/sample_data"
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in datasets().items():
        with (output / (name+".csv")).open("w",newline="",encoding="utf-8") as handle:
            writer=csv.DictWriter(handle,fieldnames=COLUMNS)
            writer.writeheader(); writer.writerows(rows)
        workbook=Workbook(); sheet=workbook.active; sheet.title="Synthetic Purchases"
        workbook.properties.creator="NOAMS"
        workbook.properties.lastModifiedBy="NOAMS"
        workbook.properties.description="Entirely fictional demonstration records"
        workbook.properties.created=datetime(2026,1,1)
        workbook.properties.modified=datetime(2026,1,1)
        sheet.append(COLUMNS)
        for row in rows:
            sheet.append([row[c] for c in COLUMNS])
        workbook.save(output / (name+".xlsx")); workbook.close()
    return output


if __name__ == "__main__":
    print("Synthetic examples generated:", generate())
