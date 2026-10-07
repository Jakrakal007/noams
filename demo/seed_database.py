"""Create and populate only the isolated demo database via the normal pipeline."""
import asyncio
from io import BytesIO
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi import UploadFile
from sqlalchemy import select
from app.core.config import settings
from app.database.migrations import run_migrations
from app.database.models import AnalysisRun
from app.database.session import SessionLocal
from app.services.analysis import analysis_service
from demo.generate_demo_data import generate


async def seed():
    generate()
    run_migrations()
    with SessionLocal() as db:
        if db.scalar(select(AnalysisRun.id).limit(1)) is not None:
            print("Demo already contains analyses; no records were added.")
            return
        for filename in ("purchases_history_demo.csv", "purchases_demo.csv"):
            content = (ROOT / "demo/sample_data" / filename).read_bytes()
            result = await analysis_service.process_upload(
                UploadFile(filename=filename, file=BytesIO(content)), db)
            print(f"{filename}: {result.valid_records} valid records, {result.findings_summary.total} findings")
    print("Database:", settings.database_url)


if __name__ == "__main__":
    asyncio.run(seed())
