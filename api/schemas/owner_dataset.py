"""Pydantic schemas for Owner Data Pathway."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DatasetUploadOut(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    file_type: str
    row_count: int | None
    message: str


class DatasetListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    file_type: str
    status: str
    row_count: int | None
    created_at: datetime


class DatasetDetailOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    file_type: str
    file_size_bytes: int
    row_count: int | None
    schema_preview: dict
    status: str
    annotation_config: dict
    converted_dataset_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class DatasetPreviewOut(BaseModel):
    id: uuid.UUID
    columns: list[str]
    rows: list[dict]
    total_rows: int | None


class AnnotationIn(BaseModel):
    labels: list[dict] = Field(default_factory=list)
    # e.g. [{"name": "quality", "type": "score", "min": 0, "max": 1}]


class AnnotationOut(BaseModel):
    id: uuid.UUID
    annotation_config: dict
    status: str
    message: str


class ConvertOut(BaseModel):
    id: uuid.UUID
    converted_dataset_id: uuid.UUID | None
    status: str
    pairs_created: int
    message: str
