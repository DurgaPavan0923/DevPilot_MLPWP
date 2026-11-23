"""API and SSE streaming endpoint integration tests with security validations."""

import pytest
from httpx import ASGITransport, AsyncClient

from devpilot.api.app import app
from devpilot.config import get_settings


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "registered_providers" in data


@pytest.mark.asyncio
async def test_session_lifecycle_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session with explicit ID
        create_resp = await client.post(
            "/api/sessions",
            json={
                "session_id": "api_test_session",
                "preset": "full",
                "provider": "mock",
                "model": "mock-model",
            },
        )
        assert create_resp.status_code == 200
        sess_data = create_resp.json()["session"]
        assert sess_data["id"] == "api_test_session"

        # Create session with server-generated ID
        auto_id_resp = await client.post(
            "/api/sessions",
            json={
                "preset": "basic",
                "provider": "mock",
                "model": "mock-model",
            },
        )
        assert auto_id_resp.status_code == 200
        auto_sess = auto_id_resp.json()["session"]
        assert auto_sess["id"].startswith("sess_")

        # Get session
        get_resp = await client.get("/api/sessions/api_test_session")
        assert get_resp.status_code == 200
        assert get_resp.json()["session"]["id"] == "api_test_session"

        # List sessions
        list_resp = await client.get("/api/sessions")
        assert list_resp.status_code == 200
        assert any(s["id"] == "api_test_session" for s in list_resp.json()["sessions"])


@pytest.mark.asyncio
async def test_repo_tree_endpoint_and_jail():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid path
        resp = await client.get("/api/repo/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert "repo_root" in data
        assert "files" in data

        # Escaping path outside workspace jail should be rejected
        escape_resp = await client.get("/api/repo/tree?path=../../etc")
        assert escape_resp.status_code == 400


@pytest.mark.asyncio
async def test_api_auth_enforcement():
    transport = ASGITransport(app=app)
    settings = get_settings()

    # Temporarily set api_key in settings
    original_key = settings.api.api_key
    settings.api.api_key = "test_secret_devpilot_token"
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Missing key on protected endpoint -> 401
            unauth_resp = await client.get("/api/providers")
            assert unauth_resp.status_code == 401

            # Invalid key -> 401
            bad_key_resp = await client.get("/api/providers", headers={"X-API-Key": "wrong_key"})
            assert bad_key_resp.status_code == 401

            # Valid X-API-Key -> 200
            valid_x_resp = await client.get(
                "/api/providers", headers={"X-API-Key": "test_secret_devpilot_token"}
            )
            assert valid_x_resp.status_code == 200

            # Valid Bearer token -> 200
            valid_bearer_resp = await client.get(
                "/api/providers",
                headers={"Authorization": "Bearer test_secret_devpilot_token"},
            )
            assert valid_bearer_resp.status_code == 200
    finally:
        settings.api.api_key = original_key


@pytest.mark.asyncio
async def test_session_control_endpoints():
    import uuid

    from devpilot.api.app import session_store

    sess_id = f"control_{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        create_resp = await client.post(
            "/api/sessions",
            json={"session_id": sess_id, "preset": "full", "provider": "mock"},
        )
        assert create_resp.status_code == 200

        # Pause
        pause_resp = await client.post(f"/api/sessions/{sess_id}/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "PAUSED"

        # Resume without turns -> 400
        bad_resume = await client.post(f"/api/sessions/{sess_id}/resume")
        assert bad_resume.status_code == 400

        # Record a message so session is resumable
        await session_store.record_message(sess_id, "user", "fix the test")

        # Resume -> 200
        resume_resp = await client.post(f"/api/sessions/{sess_id}/resume")
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "RESUMED"

        # Stop
        stop_resp = await client.post(f"/api/sessions/{sess_id}/stop")
        assert stop_resp.status_code == 200
        assert stop_resp.json()["status"] == "STOPPED"

        # Diff
        diff_resp = await client.get(f"/api/sessions/{sess_id}/diff")
        assert diff_resp.status_code == 200
        assert "diff" in diff_resp.json()

        # Rollback
        rb_resp = await client.post(
            f"/api/sessions/{sess_id}/rollback", json={"snapshot_id": "baseline"}
        )
        assert rb_resp.status_code == 200
        assert rb_resp.json()["status"] == "ROLLBACK_COMPLETED"


@pytest.mark.asyncio
async def test_repo_inspection_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # File read
        file_resp = await client.get("/api/repo/file?path=pyproject.toml")
        assert file_resp.status_code == 200
        assert "content" in file_resp.json()
        assert "devpilot" in file_resp.json()["content"]

        # Repo index
        idx_resp = await client.get("/api/repo/index?path=.")
        assert idx_resp.status_code == 200
        assert "total_files" in idx_resp.json()

        # Repo graph
        graph_resp = await client.get("/api/repo/graph?path=.")
        assert graph_resp.status_code == 200
        assert "nodes" in graph_resp.json()
        assert "edges" in graph_resp.json()


@pytest.mark.asyncio
async def test_eval_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Launch run
        launch_resp = await client.post(
            "/api/eval/runs",
            json={"presets": ["basic"], "seeds": [42], "concurrency": 1, "limit": 1},
        )
        assert launch_resp.status_code == 200
        run_id = launch_resp.json()["run_id"]

        # List runs
        list_resp = await client.get("/api/eval/runs")
        assert list_resp.status_code == 200
        assert any(r["run_id"] == run_id for r in list_resp.json()["runs"])

        # Get run
        get_run_resp = await client.get(f"/api/eval/runs/{run_id}")
        assert get_run_resp.status_code == 200
