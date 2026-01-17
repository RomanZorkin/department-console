import os
from pathlib import Path

current_dir = Path().cwd()
regions_path = current_dir / "app/data/regions/"

# Настройки для uvicorn сервера
UVICORN_HOST = os.getenv("UVICORN_HOST", "0.0.0.0")
UVICORN_PORT = int(os.getenv("UVICORN_PORT", "8032"))
UVICORN_WORKERS = int(os.getenv("UVICORN_WORKERS", "1"))
UVICORN_RELOAD = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
