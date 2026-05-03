"""
API Key ORM model (Day 27).

Long-lived authentication tokens for headless MCP/REST clients.
Replaces 15-min JWT for use cases where re-login is impractical
(Claude Code, Cursor, scripts).

Format: mgn_live_<key_id_8hex>_<secret_43chars>
Hash:   HMAC-SHA256(server_pepper, full_key)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, LargeBinary, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    # Display (safe to log/show)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prefix: Mapped[str] = mapped_column(String(32), nullable=False)

    # Secret (NEVER expose after creation)
    key_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # Authorization
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=lambda: ["tools:exec", "chat:read", "chat:write"],
    )

    # Lifecycle
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
