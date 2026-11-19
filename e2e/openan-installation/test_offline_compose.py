from pathlib import Path

import pytest

from utils.env import install_config
from utils.oc_auth import get_admin_token
from utils.shell import curl_request, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    getattr(pytest.mark, "registry-center"),
    getattr(pytest.mark, "orchestration-center"),
    pytest.mark.P0,
    pytest.mark.smoke,
]

EXPECTED_SERVICES = ("registry-center", "orchestration-center", "nginx", "portal", "postgres", "mysql")


def _generated_admin_password(bundle: Path) -> str:
    found = run(["sudo", "grep", "-r", "-l", "OC_ADMIN_INITIAL_PASSWORD", "runtime"], cwd=bundle, timeout=120)
    assert found.exit_code == 0, f"OC_ADMIN_INITIAL_PASSWORD not found under runtime/: {found.output}"
    for line in found.stdout.splitlines():
        if not line.strip():
            continue
        value = run(["sudo", "grep", "-h", "OC_ADMIN_INITIAL_PASSWORD", line.strip()], cwd=bundle, timeout=120)
        for entry in value.stdout.splitlines():
            if entry.strip().startswith("OC_ADMIN_INITIAL_PASSWORD="):
                return entry.strip().partition("=")[2].strip()
    pytest.fail("OC_ADMIN_INITIAL_PASSWORD value not parsed from generated runtime files")


def test_offline_compose_stack_healthy_single_entry(require_profile):
    require_profile("offline-node")
    cfg = install_config()
    if not cfg.offline_compose_bundle:
        pytest.skip("OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE is not set")
    bundle = Path(cfg.offline_compose_bundle)
    install = run(["sudo", "scripts/install.sh", "--eval"], cwd=bundle, timeout=3600)
    assert install.exit_code == 0, install.output
    compose_ps = run(["sudo", "docker", "compose", "-f", "runtime/compose.json", "ps"], cwd=bundle, timeout=300)
    assert compose_ps.exit_code == 0, compose_ps.output
    assert any(fragment in compose_ps.stdout for fragment in EXPECTED_SERVICES), compose_ps.output
    assert "healthy" in compose_ps.stdout, compose_ps.output
    _, entry_status = curl_request("GET", "http://127.0.0.1:8080/")
    assert entry_status == "200", "public entry on 8080 is not reachable"
    admin_password = _generated_admin_password(bundle)
    token_body, token_status, _ = get_admin_token(
        "http://127.0.0.1:8080", admin_password, evidence_stem="offline-compose-001"
    )
    assert token_status == "200", f"{token_status} {token_body}"
    assert "access_token" in token_body, token_body
    uninstall = run(["sudo", "scripts/uninstall.sh"], cwd=bundle, timeout=1200)
    assert uninstall.exit_code == 0, uninstall.output
    containers = run(["sudo", "docker", "ps", "--format", "{{.Names}}"], timeout=120)
    assert not any(fragment in containers.stdout for fragment in EXPECTED_SERVICES), containers.output
