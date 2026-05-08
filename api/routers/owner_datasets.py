"""Owner Data Pathway Router — SP-103.

Endpoints:
  POST /v1/owner/datasets/upload       → Upload CSV/JSON/JSONL
  GET  /v1/owner/datasets              → List datasets
  GET  /v1/owner/datasets/{id}         → Detail + preview
  POST /v1/owner/datasets/{id}/annotate → Set annotation config
  POST /v1/owner/datasets/{id}/convert  → Convert to preference_pairs
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from deps.auth import get_current_user
from deps.db import get_db, set_tenant_context
from models import User
from schemas.owner_dataset import (
    DatasetUploadOut,
    DatasetListItem,
    DatasetDetailOut,
    DatasetPreviewOut,
    AnnotationIn,
    AnnotationOut,
    ConvertOut,
)
from services.owner_dataset import (
    save_upload,
    list_datasets,
    get_dataset,
    annotate_dataset,
    convert_to_pairs,
)

router = APIRouter(prefix="/v1/owner/datasets", tags=["owner_datasets"])


@router.post("/upload", response_model=DatasetUploadOut)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a CSV, JSON, or JSONL dataset for training."""
    await set_tenant_context(db, str(current_user.tenant_id))

    contents = await file.read()
    try:
        record = await save_upload(
            db,
            tenant_id=current_user.tenant_id,
            owner_user_id=current_user.id,
            name=name,
            description=description,
            file_bytes=contents,
            original_filename=file.filename or "unnamed",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return DatasetUploadOut(
        id=record.id,
        name=record.name,
        status=record.status,
        file_type=record.file_type,
        row_count=record.row_count,
        message="Dataset uploaded successfully",
    )


@router.get("", response_model=list[DatasetListItem])
async def list_owner_datasets(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List datasets for the current tenant."""
    await set_tenant_context(db, str(current_user.tenant_id))
    records = await list_datasets(db, current_user.tenant_id, limit, offset)
    return [
        DatasetListItem(
            id=r.id,
            name=r.name,
            description=r.description,
            file_type=r.file_type,
            status=r.status,
            row_count=r.row_count,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.get("/{dataset_id}", response_model=DatasetDetailOut)
async def get_dataset_detail(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dataset details including schema preview."""
    await set_tenant_context(db, str(current_user.tenant_id))
    record = await get_dataset(db, dataset_id, current_user.tenant_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return DatasetDetailOut(
        id=record.id,
        name=record.name,
        description=record.description,
        file_type=record.file_type,
        file_size_bytes=record.file_size_bytes,
        row_count=record.row_count,
        schema_preview=record.schema_preview,
        status=record.status,
        annotation_config=record.annotation_config,
        converted_dataset_id=record.converted_dataset_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewOut)
async def preview_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview first few rows of a dataset."""
    await set_tenant_context(db, str(current_user.tenant_id))
    record = await get_dataset(db, dataset_id, current_user.tenant_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    preview = record.schema_preview or {}
    return DatasetPreviewOut(
        id=record.id,
        columns=preview.get("columns", []),
        rows=preview.get("sample", []),
        total_rows=record.row_count,
    )


@router.post("/{dataset_id}/annotate", response_model=AnnotationOut)
async def annotate_dataset_endpoint(
    dataset_id: uuid.UUID,
    body: AnnotationIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set annotation configuration for a dataset."""
    await set_tenant_context(db, str(current_user.tenant_id))
    record = await get_dataset(db, dataset_id, current_user.tenant_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    await annotate_dataset(db, record, body.labels)
    return AnnotationOut(
        id=record.id,
        annotation_config=record.annotation_config,
        status=record.status,
        message="Annotation config updated",
    )


@router.post("/{dataset_id}/convert", response_model=ConvertOut)
async def convert_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert dataset rows to preference_pairs for training."""
    await set_tenant_context(db, str(current_user.tenant_id))
    record = await get_dataset(db, dataset_id, current_user.tenant_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    try:
        pairs_created = await convert_to_pairs(db, record)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file missing")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    return ConvertOut(
        id=record.id,
        converted_dataset_id=record.converted_dataset_id,
        status=record.status,
        pairs_created=pairs_created,
        message=f"Converted {pairs_created} rows to preference pairs",
    )
