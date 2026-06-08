"""GitHub CI/CD deploy helpers (no gcloud / no keys in repo).

Deploy path: push to ``main`` triggers ``.github/workflows/ci.yml``, which builds
Docker images. Optional remote smoke uses ``DEPLOY_BACKEND_URL`` from the
environment (never committed).
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
from pathlib import Path

import httpx

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class DeployResult:
    success: bool
    service_url: str
    revision: str
    health_ok: bool
    health_payload: dict[str, object]
    error: str
    duration_seconds: float


def _workspace() -> Path:
    return Path(__file__).resolve().parents[2]


def read_deploy_url() -> str:
    """Optional public backend URL for post-deploy smoke (env only)."""
    return (os.getenv("DEPLOY_BACKEND_URL") or os.getenv("CLOUD_RUN_URL") or "").strip().rstrip("/")


def backend_files_changed(changed_files: list[str]) -> bool:
    if not changed_files:
        return False
    markers = (
        "backend_api.py",
        "Dockerfile.backend",
        "Dockerfile",
        "docker-compose",
        ".github/workflows/",
        "deploy/",
        "src/apex/",
        "requirements.txt",
    )
    for path in changed_files:
        for marker in markers:
            if path == marker or path.startswith(marker):
                return True
    return False


def verify_deploy_health(base_url: str, *, min_arbs: int = 0) -> tuple[bool, dict[str, object]]:
    if not base_url:
        return False, {"error": "empty base_url"}
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            health = client.get(f"{base_url}/health")
            if health.status_code != 200:
                return False, {"status_code": health.status_code, "body": health.text[:500]}
            payload = health.json()
            ok = True
            if payload.get("showcase_mode") is True and min_arbs > 0:
                arb_count = int(payload.get("arb_opportunities") or 0)
                ok = arb_count >= min_arbs
            guest = client.post(f"{base_url}/api/auth/guest")
            if guest.status_code not in (200, 201):
                ok = False
                payload["guest_status"] = guest.status_code
            arb = client.get(f"{base_url}/api/arb/opportunities")
            if arb.status_code != 200:
                ok = False
                payload["arb_list_status"] = arb.status_code
            return ok, payload
    except Exception as exc:
        return False, {"error": str(exc)}


def deploy_via_github(
    iteration: int,
    *,
    dry_run: bool = False,
) -> DeployResult:
    """Record that deploy is delegated to GitHub Actions (triggered by git push)."""
    import time

    start = time.time()
    url = read_deploy_url()
    if dry_run:
        ok, payload = verify_deploy_health(url) if url else (True, {})
        return DeployResult(
            success=True,
            service_url=url or "github-actions",
            revision="dry-run",
            health_ok=ok,
            health_payload=payload,
            error="",
            duration_seconds=time.time() - start,
        )

    LOGGER.info(
        "Iteration %s: deploy via GitHub Actions (.github/workflows/ci.yml on push to main)",
        iteration,
    )
    log_dir = _workspace() / "data" / "loop_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"iteration_{iteration:04d}_deploy.json").write_text(
        json.dumps(
            {
                "method": "github_actions",
                "workflow": ".github/workflows/ci.yml",
                "deploy_url": url,
                "note": "Images built on push; configure DOCKER_USERNAME/DOCKER_PASSWORD in GitHub Secrets to publish.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    health_ok, payload = verify_deploy_health(url) if url else (True, {})
    return DeployResult(
        success=True,
        service_url=url or "github-actions",
        revision="ci-pending",
        health_ok=health_ok,
        health_payload=payload,
        error="" if health_ok else "optional DEPLOY_BACKEND_URL health check failed",
        duration_seconds=time.time() - start,
    )
