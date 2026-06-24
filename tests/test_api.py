"""
Integration tests for the FastAPI endpoints.

These tests mock the DB, models, and Claude client so no live infrastructure
is needed. Run with:  pytest tests/test_api.py -v
"""
import sys
import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    with (
        patch("db.init_db", new_callable=AsyncMock),
        patch("main._auto_setup", new_callable=AsyncMock),
        patch("db.engine"),
        patch("main.asyncio.create_task"),
    ):
        from main import app
        app.state.bi_encoder = MagicMock()
        app.state.cross_encoder = MagicMock()
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_health_no_auth_required(self, client):
        res = client.get("/health")
        assert res.status_code != 401

    def test_health_method_not_allowed_for_post(self, client):
        res = client.post("/health")
        assert res.status_code == 405


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_query_without_key_allowed_when_no_key_configured(self, client):
        # BASINIQ_API_KEY not set → auth check is skipped
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BASINIQ_API_KEY", None)
            import importlib
            import main as m
            m._API_KEY = None
            with (
                patch("main.AsyncSessionLocal") as mock_db,
                patch("main.route_query", new_callable=AsyncMock) as mock_rq,
            ):
                mock_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                    execute=AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))),
                    get=AsyncMock(return_value=None),
                    add=MagicMock(),
                    commit=AsyncMock(),
                ))
                mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_rq.return_value = {"answer": "ok", "sources": [], "tools_used": []}
                res = client.post("/query", json={"question": "test"})
                assert res.status_code != 401

    def test_query_with_wrong_key_rejected(self, client):
        import main as m
        m._API_KEY = "correct-secret"
        res = client.post(
            "/query",
            json={"question": "test"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert res.status_code == 401
        m._API_KEY = None

    def test_query_with_correct_key_not_rejected_by_auth(self, client):
        import main as m
        m._API_KEY = "correct-secret"
        with (
            patch("main.AsyncSessionLocal") as mock_db,
            patch("main.route_query", new_callable=AsyncMock) as mock_rq,
        ):
            mock_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                execute=AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))),
                get=AsyncMock(return_value=None),
                add=MagicMock(),
                commit=AsyncMock(),
            ))
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_rq.return_value = {"answer": "ok", "sources": [], "tools_used": []}
            res = client.post(
                "/query",
                json={"question": "test"},
                headers={"X-API-Key": "correct-secret"},
            )
            assert res.status_code != 401
        m._API_KEY = None


# ---------------------------------------------------------------------------
# Query endpoint validation
# ---------------------------------------------------------------------------

class TestQueryValidation:
    def test_missing_question_returns_400(self, client):
        res = client.post("/query", json={})
        assert res.status_code == 400

    def test_empty_question_returns_400(self, client):
        res = client.post("/query", json={"question": ""})
        assert res.status_code == 400

    def test_whitespace_only_question_returns_400(self, client):
        res = client.post("/query", json={"question": "   "})
        assert res.status_code == 400

    def test_valid_question_reaches_route_query(self, client):
        import main as m
        m._API_KEY = None
        with (
            patch("main.AsyncSessionLocal") as mock_db,
            patch("main.route_query", new_callable=AsyncMock) as mock_rq,
        ):
            mock_session = MagicMock()
            mock_session.execute = AsyncMock(return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=None)
            ))
            mock_session.get = AsyncMock(return_value=None)
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_rq.return_value = {"answer": "Tourmaline has 42 wells.", "sources": [], "tools_used": ["sql"]}

            res = client.post("/query", json={"question": "How many wells does Tourmaline have?"})
            assert res.status_code == 200
            data = res.json()
            assert "answer" in data
            assert "session_id" in data

    def test_response_includes_sources_field(self, client):
        import main as m
        m._API_KEY = None
        with (
            patch("main.AsyncSessionLocal") as mock_db,
            patch("main.route_query", new_callable=AsyncMock) as mock_rq,
        ):
            mock_session = MagicMock()
            mock_session.execute = AsyncMock(return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=None)
            ))
            mock_session.get = AsyncMock(return_value=None)
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_rq.return_value = {"answer": "ok", "sources": ["directive-071, Page 5"], "tools_used": []}

            res = client.post("/query", json={"question": "H2S requirements?"})
            assert "sources" in res.json()

    def test_response_includes_tools_used_field(self, client):
        import main as m
        m._API_KEY = None
        with (
            patch("main.AsyncSessionLocal") as mock_db,
            patch("main.route_query", new_callable=AsyncMock) as mock_rq,
        ):
            mock_session = MagicMock()
            mock_session.execute = AsyncMock(return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=None)
            ))
            mock_session.get = AsyncMock(return_value=None)
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_rq.return_value = {"answer": "ok", "sources": [], "tools_used": ["sql"]}

            res = client.post("/query", json={"question": "well count?"})
            assert "tools_used" in res.json()

    def test_session_id_returned_when_not_provided(self, client):
        import main as m
        m._API_KEY = None
        with (
            patch("main.AsyncSessionLocal") as mock_db,
            patch("main.route_query", new_callable=AsyncMock) as mock_rq,
        ):
            mock_session = MagicMock()
            mock_session.execute = AsyncMock(return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=None)
            ))
            mock_session.get = AsyncMock(return_value=None)
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_rq.return_value = {"answer": "ok", "sources": [], "tools_used": []}

            res = client.post("/query", json={"question": "test?"})
            data = res.json()
            assert "session_id" in data
            assert len(data["session_id"]) == 36  # UUID format

    def test_content_type_json_required(self, client):
        res = client.post("/query", data="not json", headers={"Content-Type": "text/plain"})
        assert res.status_code in (400, 422)
