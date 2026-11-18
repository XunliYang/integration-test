from pathlib import Path

import pytest

from utils.env import install_config
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
    token_body, token_status = curl_request(
        "POST",
        "http://127.0.0.1:8080/api/v1/auth/token",
        data='{"username": "admin", "password": "' + cfg.admin_password + '"}',
        headers=["Content-Type: application/json"],
    )
    assert token_status == "200", f"{token_status} {token_body}"
    assert "token" in token_body.lower(), token_body
    uninstall = run(["sudo", "scripts/uninstall.sh"], cwd=bundle, timeout=1200)
    assert uninstall.exit_code == 0, uninstall.output
    containers = run(["sudo", "docker", "ps", "--format", "{{.Names}}"], timeout=120)
    assert not any(fragment in containers.stdout for fragment in EXPECTED_SERVICES), containers.output
