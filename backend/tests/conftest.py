import os
import tempfile
import pytest
from pathlib import Path
from starlette.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path):
    """
    Creates test settings with isolated temporary directories.
    """
    temp_data_dir = tmp_path / "data"
    temp_db_path = temp_data_dir / "database" / "test.db"
    
    settings = Settings(
        APP_NAME="JalNetra API Test",
        APP_VERSION="2.0.0-test",
        ENVIRONMENT="testing",
        DEBUG=True,
        DATA_DIR=str(temp_data_dir),
        DATABASE_URL=f"sqlite:///{temp_db_path.as_posix()}",
        FRONTEND_URL="http://localhost:5173",
    )
    return settings


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
