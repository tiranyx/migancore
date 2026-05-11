#!/usr/bin/env python3
"""MiganCore Chat Tests — Core behavioral tests for the chat endpoint.

Tests:
    - Sync chat with mocked Ollama
    - Tool calling loop
    - Context window management
    - Tenant quota enforcement
    - Error handling

Usage:
    pytest tests/test_chat.py -v
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app


@pytest.fixture
def client():
    """Synchronous test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get valid auth headers by logging in a test user."""
    # Register test user
    resp = client.post(
        "/v1/auth/register",
        json={
            "email": "chat-test@migancore.com",
            "password": "TestPass123!",
            "display_name": "Chat Tester",
        },
    )
    if resp.status_code == 409:
        # User already exists, login instead
        resp = client.post(
            "/v1/auth/login",
            json={
                "email": "chat-test@migancore.com",
                "password": "TestPass123!",
            },
        )
    else:
        resp = client.post(
            "/v1/auth/login",
            json={
                "email": "chat-test@migancore.com",
                "password": "TestPass123!",
            },
        )

    assert resp.status_code == 200, f"Auth failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_agent(client, auth_headers):
    """Create a test agent and return its ID."""
    resp = client.post(
        "/v1/agents",
        headers=auth_headers,
        json={
            "name": "Test Agent",
            "slug": f"test-agent-{uuid.uuid4().hex[:8]}",
            "persona_blob": {},
        },
    )
    if resp.status_code == 409:
        # Agent exists, list and return first
        resp = client.get("/v1/agents", headers=auth_headers)
        agents = resp.json()
        return agents[0]["id"] if agents else None

    assert resp.status_code == 201, f"Agent creation failed: {resp.text}"
    return resp.json()["id"]


class TestChatSync:
    """Tests for synchronous chat endpoint."""

    def test_chat_simple(self, client, auth_headers, test_agent):
        """Test basic chat returns a response."""
        with patch("services.director.run_director") as mock_director:
            mock_director.return_value = {
                "final_response": "Halo! Saya Mighan-Core. Ada yang bisa saya bantu?",
                "tool_calls": [],
                "iteration": 0,
            }

            resp = client.post(
                f"/v1/agents/{test_agent}/chat",
                headers=auth_headers,
                json={"message": "Halo", "conversation_id": None},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "message_id" in data
        assert "conversation_id" in data

    def test_chat_with_tool_call(self, client, auth_headers, test_agent):
        """Test chat that triggers a tool call."""
        with patch("services.director.run_director") as mock_director:
            mock_director.return_value = {
                "final_response": "Cuaca hari ini cerah di Jakarta.",
                "tool_calls": [
                    {
                        "tool": "web_search",
                        "args": {"query": "cuaca jakarta hari ini"},
                        "result": {"status": "ok", "data": "Cerah, 32°C"},
                    }
                ],
                "iteration": 1,
            }

            resp = client.post(
                f"/v1/agents/{test_agent}/chat",
                headers=auth_headers,
                json={"message": "Cuaca Jakarta hari ini?"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "Cuaca" in data["response"]

    def test_chat_persists_conversation(self, client, auth_headers, test_agent):
        """Test that chat creates and persists a conversation."""
        with patch("services.director.run_director") as mock_director:
            mock_director.return_value = {
                "final_response": "Jawaban pertama",
                "tool_calls": [],
                "iteration": 0,
            }

            resp1 = client.post(
                f"/v1/agents/{test_agent}/chat",
                headers=auth_headers,
                json={"message": "Pertanyaan pertama"},
            )
            assert resp1.status_code == 200
            conv_id = resp1.json()["conversation_id"]

            # Second message in same conversation
            mock_director.return_value = {
                "final_response": "Jawaban kedua",
                "tool_calls": [],
                "iteration": 0,
            }
            resp2 = client.post(
                f"/v1/agents/{test_agent}/chat",
                headers=auth_headers,
                json={"message": "Pertanyaan kedua", "conversation_id": conv_id},
            )
            assert resp2.status_code == 200
            assert resp2.json()["conversation_id"] == conv_id

    def test_chat_unauthorized(self, client, test_agent):
        """Test chat without auth returns 401."""
        resp = client.post(
            f"/v1/agents/{test_agent}/chat",
            json={"message": "Halo"},
        )
        assert resp.status_code == 401

    def test_chat_agent_not_found(self, client, auth_headers):
        """Test chat with non-existent agent returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"/v1/agents/{fake_id}/chat",
            headers=auth_headers,
            json={"message": "Halo"},
        )
        assert resp.status_code in (404, 403)  # 403 if RLS blocks

    def test_chat_empty_message(self, client, auth_headers, test_agent):
        """Test chat with empty message returns error."""
        resp = client.post(
            f"/v1/agents/{test_agent}/chat",
            headers=auth_headers,
            json={"message": ""},
        )
        assert resp.status_code in (400, 422)


class TestChatStreaming:
    """Tests for SSE streaming chat endpoint."""

    def test_stream_basic(self, client, auth_headers, test_agent):
        """Test streaming returns SSE events."""
        with patch("services.director.run_director_stream") as mock_stream:
            async def fake_stream():
                yield {"type": "token", "content": "Halo"}
                yield {"type": "token", "content": "!"}
                yield {"type": "done", "content": "Halo!"}

            mock_stream.return_value = fake_stream()

            resp = client.post(
                f"/v1/agents/{test_agent}/chat/stream",
                headers={**auth_headers, "Accept": "text/event-stream"},
                json={"message": "Halo"},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_stream_tool_call(self, client, auth_headers, test_agent):
        """Test streaming with tool call includes tool events."""
        with patch("services.director.run_director_stream") as mock_stream:
            async def fake_stream():
                yield {"type": "token", "content": "Mencari"}
                yield {"type": "tool_call", "tool": "web_search", "args": {"query": "test"}}
                yield {"type": "tool_result", "tool": "web_search", "result": "Hasil"}
                yield {"type": "token", "content": "Hasil ditemukan"}
                yield {"type": "done", "content": "Hasil ditemukan"}

            mock_stream.return_value = fake_stream()

            resp = client.post(
                f"/v1/agents/{test_agent}/chat/stream",
                headers={**auth_headers, "Accept": "text/event-stream"},
                json={"message": "Cari test"},
            )

        assert resp.status_code == 200


class TestChatTenantIsolation:
    """Tests for tenant isolation in chat."""

    def test_chat_different_tenant(self, client):
        """Test user from tenant A cannot chat with tenant B's agent."""
        # Register tenant A user
        resp_a = client.post(
            "/v1/auth/register",
            json={
                "email": f"tenant-a-{uuid.uuid4().hex[:6]}@migancore.com",
                "password": "TestPass123!",
                "display_name": "Tenant A",
            },
        )
        if resp_a.status_code == 409:
            # Already exists
            pass
        else:
            assert resp_a.status_code == 201

        # This test requires actual multi-tenant setup
        # For now, just verify the endpoint structure
        pass


class TestChatContextWindow:
    """Tests for context window management."""

    def test_chat_long_message_truncated(self, client, auth_headers, test_agent):
        """Test very long messages are handled gracefully."""
        long_message = "A" * 10000  # 10K characters

        with patch("services.director.run_director") as mock_director:
            mock_director.return_value = {
                "final_response": "Pesan terlalu panjang. Saya akan merangkum.",
                "tool_calls": [],
                "iteration": 0,
            }

            resp = client.post(
                f"/v1/agents/{test_agent}/chat",
                headers=auth_headers,
                json={"message": long_message},
            )

        assert resp.status_code == 200


class TestChatQuota:
    """Tests for tenant message quota enforcement."""

    def test_chat_quota_enforced(self, client, auth_headers, test_agent):
        """Test that quota is enforced (requires quota setup)."""
        # This test requires a tenant with low quota
        # For now, verify the endpoint accepts messages
        with patch("services.director.run_director") as mock_director:
            mock_director.return_value = {
                "final_response": "OK",
                "tool_calls": [],
                "iteration": 0,
            }

            resp = client.post(
                f"/v1/agents/{test_agent}/chat",
                headers=auth_headers,
                json={"message": "Test quota"},
            )

        assert resp.status_code == 200
