from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import Response

from ..services.passport_processing import PassportProcessingError, PassportProcessingService
from ..services.xlsx_exporter import build_passports_xlsx


router = APIRouter()
processing_service = PassportProcessingService()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/passports/extract")
async def extract_passports(files: list[UploadFile] = File(...)) -> Response:
    if not files:
        raise HTTPException(status_code=400, detail="Нужно загрузить хотя бы один PDF-файл")

    try:
        passports = await processing_service.process_uploads(files)
        xlsx_bytes = build_passports_xlsx(passports)
    except PassportProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки документов: {exc}") from exc

    filename = "passport_export.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Некорректный запрос. Загрузите PDF в поле files."},
    )
