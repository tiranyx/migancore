"""
Owner Dataset Service — upload, preview, annotate, convert.

Files are stored in WORKSPACE_DIR/owner_datasets/{tenant_id}/
Max file size: 50 MB.
Supported formats: csv, json, jsonl.
"""

from __future__ import annotations

import csv
import json
import os
import uuid
from pathlib import Path
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.owner_dataset import OwnerDataset
from models.preference_pair import PreferencePair

logger = structlog.get_logger()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", "/app/workspace"))
STORAGE = WORKSPACE / "owner_datasets"


def _tenant_dir(tenant_id: uuid.UUID) -> Path:
    d = STORAGE / str(tenant_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _detect_file_type(filename: str) -> str:
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext in ("csv",):
        return "csv"
    if ext in ("json",):
        return "json"
    if ext in ("jsonl", "ndjson"):
        return "jsonl"
    return "unknown"


def _extract_preview(file_path: Path, file_type: str, max_rows: int = 5) -> dict:
    """Return column names and first few rows."""
    preview = {"columns": [], "sample": []}
    try:
        if file_type == "csv":
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                preview["columns"] = reader.fieldnames or []
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    preview["sample"].append(row)
        elif file_type == "json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    preview["columns"] = list(data[0].keys())
                    preview["sample"] = data[:max_rows]
                elif isinstance(data, dict):
                    preview["columns"] = list(data.keys())
                    preview["sample"] = [data]
        elif file_type == "jsonl":
            with open(file_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= max_rows:
                        break
                    obj = json.loads(line)
                    if i == 0:
                        preview["columns"] = list(obj.keys())
                    preview["sample"].append(obj)
    except Exception as exc:
        logger.warning("owner_dataset.preview_failed", error=str(exc))
    return preview


def _count_rows(file_path: Path, file_type: str) -> int | None:
    try:
        if file_type == "csv":
            with open(file_path, "r", encoding="utf-8") as f:
                return sum(1 for _ in csv.reader(f)) - 1  # minus header
        elif file_type == "json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return len(data) if isinstance(data, list) else 1
        elif file_type == "jsonl":
            with open(file_path, "r", encoding="utf-8") as f:
                return sum(1 for _ in f)
    except Exception as exc:
        logger.warning("owner_dataset.row_count_failed", error=str(exc))
    return None


async def save_upload(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    name: str,
    description: Optional[str],
    file_bytes: bytes,
    original_filename: str,
) -> OwnerDataset:
    """Persist uploaded file and create OwnerDataset record."""
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError(f"File exceeds {MAX_FILE_SIZE} bytes limit")

    file_type = _detect_file_type(original_filename)
    if file_type == "unknown":
        raise ValueError("Unsupported file type. Use csv, json, or jsonl.")

    # Save to disk
    file_id = uuid.uuid4()
    tenant_dir = _tenant_dir(tenant_id)
    file_path = tenant_dir / f"{file_id}.{file_type}"
    file_path.write_bytes(file_bytes)

    # Preview + row count
    preview = _extract_preview(file_path, file_type)
    row_count = _count_rows(file_path, file_type)

    record = OwnerDataset(
        tenant_id=tenant_id,
        owner_user_id=owner_user_id,
        name=name,
        description=description,
        file_path=str(file_path),
        file_type=file_type,
        file_size_bytes=len(file_bytes),
        row_count=row_count,
        schema_preview=preview,
        status="ready",
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def list_datasets(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[OwnerDataset]:
    result = await session.execute(
        select(OwnerDataset)
        .where(OwnerDataset.tenant_id == tenant_id)
        .order_by(OwnerDataset.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_dataset(
    session: AsyncSession,
    dataset_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> OwnerDataset | None:
    result = await session.execute(
        select(OwnerDataset).where(
            OwnerDataset.id == dataset_id,
            OwnerDataset.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def annotate_dataset(
    session: AsyncSession,
    dataset: OwnerDataset,
    annotation_config: dict,
) -> OwnerDataset:
    dataset.annotation_config = annotation_config
    dataset.status = "annotated"
    await session.commit()
    await session.refresh(dataset)
    return dataset


async def convert_to_pairs(
    session: AsyncSession,
    dataset: OwnerDataset,
) -> int:
    """Convert owner dataset rows to preference_pairs.

    Currently supports simple JSON/JSONL with {prompt, chosen, rejected} fields.
    Returns number of pairs created.
    """
    if not Path(dataset.file_path).exists():
        raise FileNotFoundError("Dataset file missing")

    created = 0
    file_path = Path(dataset.file_path)

    try:
        if dataset.file_type == "json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = [data]
                for row in data:
                    pair = _row_to_pair(row, dataset)
                    if pair:
                        session.add(pair)
                        created += 1

        elif dataset.file_type == "jsonl":
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    row = json.loads(line)
                    pair = _row_to_pair(row, dataset)
                    if pair:
                        session.add(pair)
                        created += 1

        elif dataset.file_type == "csv":
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pair = _row_to_pair(row, dataset)
                    if pair:
                        session.add(pair)
                        created += 1

        if created > 0:
            dataset.status = "converted"
            await session.commit()
            await session.refresh(dataset)

    except Exception as exc:
        dataset.status = "error"
        await session.commit()
        logger.error("owner_dataset.convert_failed", dataset_id=str(dataset.id), error=str(exc))
        raise

    return created


def _row_to_pair(row: dict, dataset: OwnerDataset) -> PreferencePair | None:
    """Convert a single row to PreferencePair if valid."""
    prompt = row.get("prompt") or row.get("instruction") or row.get("input")
    chosen = row.get("chosen") or row.get("response") or row.get("output")
    rejected = row.get("rejected") or row.get("bad_response")

    if not prompt or not chosen:
        return None

    # If no rejected, use a placeholder (worker fills later)
    if not rejected:
        rejected = "__AWAITING_REJECTED__"

    return PreferencePair(
        prompt=str(prompt),
        chosen=str(chosen),
        rejected=str(rejected),
        judge_score=float(row.get("score", 0.5)),
        judge_model="owner_dataset",
        source_method=f"owner_dataset:{dataset.file_type}",
    )
