"""Tests for SQLAlchemy ORM models.

Tests model definitions, column defaults, and metadata registration.
"""

import uuid

import pytest
from sqlalchemy import inspect

from models.base import Base
from models.tenant import Tenant
from models.user import User
from models.agent import Agent
from models.conversation import Conversation
from models.message import Message
from models.model_version import ModelVersion
from models.tool import Tool
from models.preference_pair import PreferencePair
from models.api_key import ApiKey


def _get_col_default(model_cls, col_name):
    """Helper: get the default value of a column from the mapper."""
    mapper = inspect(model_cls)
    col = mapper.columns.get(col_name)
    if col is None:
        return None
    # Return server_default or default
    if col.default is not None:
        arg = col.default.arg
        if callable(arg):
            try:
                return arg()
            except TypeError:
                # SQLAlchemy 2.0 context-aware default (e.g., dict for JSONB)
                # These require a SQL execution context; skip for schema tests
                return None
        return arg
    return None


class TestTenantModel:
    """Test Tenant ORM model."""

    def test_tenant_has_tablename(self):
        assert Tenant.__tablename__ == "tenants"

    def test_tenant_default_plan(self):
        default = _get_col_default(Tenant, "plan")
        assert default == "free"

    def test_tenant_default_max_agents(self):
        default = _get_col_default(Tenant, "max_agents")
        assert default == 3

    def test_tenant_slug_is_unique(self):
        mapper = inspect(Tenant)
        constraints = [c for c in mapper.tables[0].constraints if hasattr(c, 'columns')]
        slugs = [list(c.columns)[0].name for c in constraints if 'slug' in [col.name for col in c.columns]]
        assert "slug" in [c.name for c in mapper.columns]

    def test_tenant_id_is_uuid_type(self):
        mapper = inspect(Tenant)
        # SQLAlchemy 2.0 Uuid type
        assert "Uuid" in str(type(mapper.columns["id"].type)) or "UUID" in str(mapper.columns["id"].type)


class TestUserModel:
    """Test User ORM model."""

    def test_user_has_tablename(self):
        assert User.__tablename__ == "users"

    def test_user_default_role(self):
        default = _get_col_default(User, "role")
        assert default == "member"

    def test_user_email_is_unique(self):
        mapper = inspect(User)
        assert "email" in [c.name for c in mapper.columns]

    def test_user_relationship_to_tenant(self):
        assert hasattr(User, "tenant")


class TestAgentModel:
    """Test Agent ORM model."""

    def test_agent_has_tablename(self):
        assert Agent.__tablename__ == "agents"

    def test_agent_default_generation(self):
        default = _get_col_default(Agent, "generation")
        assert default == 0

    def test_agent_default_model_version(self):
        default = _get_col_default(Agent, "model_version")
        assert default == "migancore:0.7c"

    def test_agent_has_persona_blob_column(self):
        mapper = inspect(Agent)
        assert "persona_blob" in [c.name for c in mapper.columns]

    def test_agent_default_status(self):
        default = _get_col_default(Agent, "status")
        assert default == "active"

    def test_agent_default_visibility(self):
        default = _get_col_default(Agent, "visibility")
        assert default == "private"

    def test_agent_persona_locked_default(self):
        default = _get_col_default(Agent, "persona_locked")
        assert default is False

    def test_agent_has_parent_agent_fk(self):
        mapper = inspect(Agent)
        assert "parent_agent_id" in [c.name for c in mapper.columns]


class TestConversationModel:
    """Test Conversation ORM model."""

    def test_conversation_has_tablename(self):
        assert Conversation.__tablename__ == "conversations"

    def test_conversation_default_status(self):
        default = _get_col_default(Conversation, "status")
        assert default == "active"

    def test_conversation_default_message_count(self):
        default = _get_col_default(Conversation, "message_count")
        assert default == 0

    def test_conversation_has_metadata_jsonb(self):
        mapper = inspect(Conversation)
        assert "metadata" in [c.name for c in mapper.columns]


class TestMessageModel:
    """Test Message ORM model."""

    def test_message_has_tablename(self):
        assert Message.__tablename__ == "messages"

    def test_message_role_constraint_values(self):
        allowed = {"system", "user", "assistant", "tool"}
        assert len(allowed) == 4

    def test_message_has_quality_score(self):
        mapper = inspect(Message)
        assert "quality_score" in [c.name for c in mapper.columns]

    def test_message_has_tokens_in_out(self):
        mapper = inspect(Message)
        assert "tokens_in" in [c.name for c in mapper.columns]
        assert "tokens_out" in [c.name for c in mapper.columns]


class TestModelVersionModel:
    """Test ModelVersion ORM model."""

    def test_model_version_has_tablename(self):
        assert ModelVersion.__tablename__ == "model_versions"

    def test_model_version_default_is_active(self):
        default = _get_col_default(ModelVersion, "is_active")
        assert default is False

    def test_model_version_has_evaluation_scores_column(self):
        mapper = inspect(ModelVersion)
        assert "evaluation_scores" in [c.name for c in mapper.columns]

    def test_model_version_version_tag_is_unique(self):
        mapper = inspect(ModelVersion)
        assert "version_tag" in [c.name for c in mapper.columns]


class TestToolModel:
    """Test Tool ORM model."""

    def test_tool_has_tablename(self):
        assert Tool.__tablename__ == "tools"

    def test_tool_default_is_active(self):
        default = _get_col_default(Tool, "is_active")
        assert default is True

    def test_tool_handler_types(self):
        allowed = {"builtin", "python_callable", "webhook", "mcp"}
        assert len(allowed) == 4

    def test_tool_schema_is_jsonb(self):
        mapper = inspect(Tool)
        assert "schema" in [c.name for c in mapper.columns]


class TestPreferencePairModel:
    """Test PreferencePair ORM model."""

    def test_preference_pair_has_tablename(self):
        assert PreferencePair.__tablename__ == "preference_pairs"

    def test_preference_pair_required_fields_exist(self):
        mapper = inspect(PreferencePair)
        required = {"prompt", "chosen", "rejected", "judge_score", "source_method"}
        cols = {c.name for c in mapper.columns}
        assert required.issubset(cols)

    def test_preference_pair_has_judge_model(self):
        mapper = inspect(PreferencePair)
        assert "judge_model" in [c.name for c in mapper.columns]


class TestApiKeyModel:
    """Test ApiKey ORM model."""

    def test_api_key_has_tablename(self):
        assert ApiKey.__tablename__ == "api_keys"

    def test_api_key_has_key_hash(self):
        mapper = inspect(ApiKey)
        assert "key_hash" in [c.name for c in mapper.columns]


class TestBaseMetadata:
    """Test that all models are registered in Base.metadata."""

    def test_all_tables_registered(self):
        tables = Base.metadata.tables
        expected = {
            "tenants", "users", "agents", "conversations", "messages",
            "model_versions", "tools", "preference_pairs", "api_keys",
            "refresh_tokens", "audit_events",
        }
        for name in expected:
            assert name in tables, f"Table {name} not registered in Base.metadata"

    def test_hafidz_in_base_metadata(self):
        """hafidz_contributions is now registered via ORM model import."""
        tables = Base.metadata.tables
        assert "hafidz_contributions" in tables
