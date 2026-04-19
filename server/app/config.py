from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVER_ROOT.parent

STORAGE_ROOT = SERVER_ROOT / "storage"
UPLOADS_DIR = STORAGE_ROOT / "uploads"
PROCESSED_DIR = STORAGE_ROOT / "processed"
EXPORT_DIR = STORAGE_ROOT / "export"

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def ensure_storage_dirs() -> None:
    for directory in (UPLOADS_DIR, PROCESSED_DIR, EXPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
