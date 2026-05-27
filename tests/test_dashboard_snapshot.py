"""Dashboard snapshot endpoint (Phase 1)."""

from __future__ import annotations

from fastapi.testclient import TestClient

import backend_api


def test_dashboard_snapshot_returns_core_fields():
    client = TestClient(backend_api.app)
    r = client.get("/api/dashboard/snapshot")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "snapshot"
    assert "account" in body
    assert "positions" in body
    assert "opportunities" in body
    assert "events" in body


def test_health_exposes_scheduler_mode():
    client = TestClient(backend_api.app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "scheduler" in body
    assert "mode" in body["scheduler"]
