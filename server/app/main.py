from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router, validation_exception_handler
from .config import ALLOWED_ORIGINS, ensure_storage_dirs


def create_app() -> FastAPI:
    ensure_storage_dirs()

    app = FastAPI(
        title="Passport OCR API",
        version="1.0.0",
        description="HTTP API for PDF passport extraction and XLSX export.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(router, prefix="/api")
    return app


app = create_app()
