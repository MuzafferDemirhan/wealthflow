import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.export import Export, ExportStatus
from app.models.user import User
from app.schemas.export import ExportCreateRequest, ExportRead
from app.services import export_service

router = APIRouter()


@router.post("", response_model=ExportRead, status_code=status.HTTP_201_CREATED)
async def create_export(
    body: ExportCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Generate a report export (PDF or CSV) asynchronously."""
    export = export_service.generate_export(
        db,
        user_id=current_user.id,
        report_type=body.report_type,
        fmt=body.format,
        date_from=body.date_from,
        date_to=body.date_to,
    )
    db.commit()
    return export


@router.get("", response_model=list[ExportRead])
async def list_exports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all exports for the current user, newest first."""
    stmt = (
        select(Export)
        .where(Export.user_id == current_user.id)
        .order_by(Export.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/{export_id}/download")
async def download_export(
    export_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Download a completed export file."""
    export = db.get(Export, export_id)
    if export is None or export.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")

    if export.status != ExportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export is {export.status.value}, not completed",
        )

    return FileResponse(
        path=export.file_path,
        filename=export.filename,
        media_type="application/octet-stream",
    )
