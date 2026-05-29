"""Cloud Run deploy + post-deploy verification for the autonomous loop."""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path

import httpx

LOGGER = logging.getLogger(__name__)

URL_FILE = Path("/home/aarav/Aarav/Autopilot/data/cloud_run_url.txt")
FRONTEND_URL_FILE = Path("/home/aarav/Aarav/Autopilot/data/cloud_run_frontend_url.txt")
URLS_FILE = Path("/home/aarav/Aarav/Autopilot/data/cloud_run_urls.json")


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
    return Path("/home/aarav/Aarav/Autopilot")


def read_cloud_run_url() -> str:
    env_url = os.getenv("CLOUD_RUN_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")
    if URLS_FILE.exists():
        try:
            data = json.loads(URLS_FILE.read_text(encoding="utf-8"))
            backend = str(data.get("backend") or "").strip()
            if backend:
                return backend.rstrip("/")
        except Exception:
            pass
    if URL_FILE.exists():
        return URL_FILE.read_text(encoding="utf-8").strip().rstrip("/")
    return ""


def read_cloud_run_frontend_url() -> str:
    env_url = os.getenv("CLOUD_RUN_FRONTEND_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")
    if URLS_FILE.exists():
        try:
            data = json.loads(URLS_FILE.read_text(encoding="utf-8"))
            frontend = str(data.get("frontend") or "").strip()
            if frontend:
                return frontend.rstrip("/")
        except Exception:
            pass
    if FRONTEND_URL_FILE.exists():
        return FRONTEND_URL_FILE.read_text(encoding="utf-8").strip().rstrip("/")
    return ""


def save_cloud_run_url(url: str) -> None:
    URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    URL_FILE.write_text(url.rstrip("/") + "\n", encoding="utf-8")


def gcloud_available() -> bool:
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        project = (result.stdout or "").strip()
        return result.returncode == 0 and project not in ("", "(unset)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def backend_files_changed(changed_files: list[str]) -> bool:
    if not changed_files:
        return False
    markers = (
        "backend_api.py",
        "Dockerfile.cloudrun",
        "cloudbuild.yaml",
        ".gcloudignore",
        "deploy/",
        "src/apex/",
    )
    for path in changed_files:
        for marker in markers:
            if path == marker or path.startswith(marker):
                return True
    return False


def verify_cloud_health(base_url: str, *, min_arbs: int = 1) -> tuple[bool, dict[str, object]]:
    if not base_url:
        return False, {"error": "empty base_url"}
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            health = client.get(f"{base_url}/health")
            if health.status_code != 200:
                return False, {"status_code": health.status_code, "body": health.text[:500]}
            payload = health.json()
            ok = True
            if payload.get("showcase_mode") is True:
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


def deploy_to_cloud_run(
    iteration: int,
    *,
    dry_run: bool = False,
    skip_secrets: bool = True,
) -> DeployResult:
    start = time.time()
    workspace = _workspace()
    deploy_script = workspace / "deploy" / "deploy_cloud_run.sh"

    if dry_run:
        url = read_cloud_run_url() or "https://example.run.app"
        ok, payload = verify_cloud_health(url) if read_cloud_run_url() else (True, {})
        return DeployResult(
            success=True,
            service_url=url,
            revision="dry-run",
            health_ok=ok,
            health_payload=payload,
            error="",
            duration_seconds=time.time() - start,
        )

    if not gcloud_available():
        return DeployResult(
            success=False,
            service_url=read_cloud_run_url(),
            revision="",
            health_ok=False,
            health_payload={},
            error="gcloud not configured (run: gcloud auth login && gcloud config set project <id>)",
            duration_seconds=time.time() - start,
        )

    if not deploy_script.is_file():
        return DeployResult(
            success=False,
            service_url="",
            revision="",
            health_ok=False,
            health_payload={},
            error=f"missing deploy script: {deploy_script}",
            duration_seconds=time.time() - start,
        )

    env = os.environ.copy()
    if skip_secrets:
        env["SKIP_SECRETS"] = "1"

    LOGGER.info("Deploying iteration %s via %s", iteration, deploy_script)
    try:
        proc = subprocess.run(
            ["bash", str(deploy_script)],
            cwd=workspace,
            capture_output=True,
            text=True,
            env=env,
            timeout=int(os.getenv("LOOP_DEPLOY_TIMEOUT_SEC", "1200")),
        )
    except subprocess.TimeoutExpired:
        return DeployResult(
            success=False,
            service_url=read_cloud_run_url(),
            revision="",
            health_ok=False,
            health_payload={},
            error="deploy timed out",
            duration_seconds=time.time() - start,
        )

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    url_match = re.search(r">> Deployed:\s*(https://\S+)", combined)
    service_url = url_match.group(1).rstrip("/") if url_match else read_cloud_run_url()
    if service_url:
        save_cloud_run_url(service_url)

    revision = ""
    rev_match = re.search(r"Revision\s+\[\S+\]\s+(?:has been deployed|deployed)", combined, re.I)
    if rev_match:
        revision = rev_match.group(0)[:120]

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "deploy failed")[-2000:]
        _save_deploy_log(iteration, proc.returncode, combined, service_url, False, {})
        return DeployResult(
            success=False,
            service_url=service_url,
            revision=revision,
            health_ok=False,
            health_payload={},
            error=err,
            duration_seconds=time.time() - start,
        )

    health_ok, payload = verify_cloud_health(service_url)
    _save_deploy_log(iteration, 0, combined, service_url, health_ok, payload)
    return DeployResult(
        success=health_ok,
        service_url=service_url,
        revision=revision,
        health_ok=health_ok,
        health_payload=payload,
        error="" if health_ok else "post-deploy health verification failed",
        duration_seconds=time.time() - start,
    )


def _save_deploy_log(
    iteration: int,
    exit_code: int,
    log_text: str,
    url: str,
    health_ok: bool,
    health_payload: dict[str, object],
) -> None:
    workspace = _workspace()
    log_dir = workspace / "data" / "loop_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    summary_path = log_dir / f"iteration_{iteration:04d}_deploy.json"
    summary_path.write_text(
        json.dumps(
            {
                "exit_code": exit_code,
                "service_url": url,
                "health_ok": health_ok,
                "health_payload": health_payload,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (log_dir / f"iteration_{iteration:04d}_deploy.log").write_text(log_text[-50000:], encoding="utf-8")
