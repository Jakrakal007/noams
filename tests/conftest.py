import pytest
from pathlib import Path
import shutil
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.core.config import settings
from app.main import app


@pytest.fixture
def client(monkeypatch):
    upload_dir = Path("data/test_uploads") / str(uuid4())
    monkeypatch.setattr(settings, "noams_upload_dir", upload_dir)
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db: Session = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.test_session_factory = TestingSession
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    shutil.rmtree(upload_dir, ignore_errors=True)
    try:
        upload_dir.parent.rmdir()
    except OSError:
        pass
