from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.database import get_db
from app.services.storage_service import storage_service
from app.schemas import StorageStatusResponse, StorageDirectoryStatus

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.get("/status", response_model=StorageStatusResponse, summary="Storage and database status")
def get_storage_status(db: Session = Depends(get_db)) -> StorageStatusResponse:
    # Check database status
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check key directories
    subdirs = [
        "data",
        "database",
        "water_bodies",
        "scenes",
        "processed",
        "tiles",
        "cache",
        "exports",
        "manifests",
    ]

    directories_summary = {}
    details = {}

    for sub in subdirs:
        dir_path = (
            storage_service.base_dir
            if sub == "data"
            else storage_service.base_dir / sub
        )
        exists = dir_path.exists()
        is_dir = dir_path.is_dir() if exists else False
        file_count = len(list(dir_path.iterdir())) if is_dir else 0

        status_str = "ok" if (exists and is_dir) else "missing"
        directories_summary[sub] = status_str

        # Only present relative path to avoid leaking sensitive host filesystem details
        rel_str = f"./data/{sub}" if sub != "data" else "./data"
        details[sub] = StorageDirectoryStatus(
            path=rel_str,
            exists=exists,
            is_directory=is_dir,
            file_count=file_count,
        )

    return StorageStatusResponse(
        database={
            "status": db_status,
            "engine": "sqlite",
            "url_type": "sqlite_local",
        },
        directories=directories_summary,
        details=details,
    )
