"""BOQ upload and processing routes."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.services.cost_engine import InvalidWorkbookError, process_boq_upload


router = APIRouter(tags=["boq"])


@router.post("/upload-boq")
async def upload_boq(
    file: UploadFile = File(...),
    region: str = Form("Nairobi"),
    response_format: str = Form("json"),
):
    """Accept an Excel BOQ, process it in memory, and return JSON or XLSX."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Only Excel workbooks (.xlsx, .xlsm) are supported.")

    try:
        payload = await file.read()
        result = process_boq_upload(file_bytes=payload, filename=file.filename, region=region)
    except InvalidWorkbookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=500, detail="Failed to process BOQ upload.") from exc

    if response_format.lower() == "excel":
        headers = {"Content-Disposition": f'attachment; filename="{result.output_filename}"'}
        return StreamingResponse(
            result.workbook_stream(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    if response_format.lower() != "json":
        raise HTTPException(status_code=400, detail="response_format must be either 'json' or 'excel'.")
    return JSONResponse(result.model_dump())
