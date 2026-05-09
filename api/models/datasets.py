"""
Datasets table — registered manually in Base.metadata because there is no
ORM model for it (managed via raw SQL / migrations).  Required so that
OwnerDataset.converted_dataset_id FK resolves during Base.metadata.create_all().
"""

from sqlalchemy import Table, Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


datasets_table = Table(
    "datasets",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("source_type", String(32), nullable=False),
    Column("size_samples", Integer, nullable=True),
    Column("hf_dataset_uri", String(512), nullable=True),
    Column("local_path", String(512), nullable=True),
    Column("parent_dataset_id", UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True),
    Column("quality_avg", Float, nullable=True),
    Column("language", String(8), nullable=True, default="id"),
    Column("domain", String(64), nullable=True),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    extend_existing=True,
)
