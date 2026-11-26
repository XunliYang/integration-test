import json
from pathlib import Path

import pytest

from utils.env import install_config
from utils.oc_auth import TOKEN_FIELDS, get_admin_token
from utils.shell import curl_request, register_secret, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.P0,
    pytest.mark.smoke,
]

CORE_SERVICES = {"registry-center", "orchestration-center", "openan-nginx"}
DATABASE_SERVICES = {"openan-mysql", "openan-postgres"}


def _json_items(text: str) -> list[dict]:
    text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = [json.loads(line) for line in text.splitlines() if line.strip()]
    return parsed if isinstance(parsed, list) else [parsed]


def _stack(bundle: Path) -> dict:
    compose = run(["sudo", "cat", "runtime/compose.json"], cwd=bundle, timeout=120)
    assert compose.exit_code == 0, f"runtime/compose.json is not readable: {compose.stderr}"
    return json.loads(compose.stdout)


def _service_status(bundle: Path) -> dict[str, tuple[str, str]]:
    ps = run(
        ["sudo", "docker", "compose", "-f", "runtime/compose.json", "ps", "--format", "json"],
        cwd=bundle,
        timeout=300,
    )
    assert ps.exit_code == 0, ps.output
    items = [{key.lower(): value for key, value in item.items()} for item in _json_items(ps.stdout)]
    assert all("health" in item for item in items), (
        f"docker compose >= 2.20 is required (ps --format json has no health field): {items}"
    )
    return {str(item["service"]): (str(item.get("state")), str(item.get("health"))) for item in items}


def _uninstall(bundle: Path):
    return run(["sudo", "scripts/uninstall.sh"], cwd=bundle, timeout=1200)


def _reset_state(bundle: Path):
    down = run(
        ["sudo", "docker", "compose", "-f", "runtime/compose.json", "down", "--volumes", "--remove-orphans"],
        cwd=bundle,
        timeout=300,
    )
    for service in ("registry-center", "orchestration-center"):
        run(["sudo", "rm", "-rf", f"runtime/{service}/data"], cwd=bundle, timeout=120)
    return down


def _admin_password(bundle: Path) -> str:
    environment = _stack(bundle)["services"]["orchestration-center"]["environment"]
    password = environment.get("OC_ADMIN_INITIAL_PASSWORD", "").replace("$$", "$")
    assert password, "OC_ADMIN_INITIAL_PASSWORD is missing from runtime/compose.json"
    register_secret(password)
    return password


@getattr(pytest.mark, "FIT-openan-installation-offline-compose-001")
@getattr(pytest.mark, "26-winter")
@getattr(pytest.mark, "registry-center")
@getattr(pytest.mark, "orchestration-center")
def test_offline_compose_stack_healthy_single_entry(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    if not cfg.offline_compose_bundle:
        pytest.skip("OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE is not set")
    bundle = Path(cfg.offline_compose_bundle)
    cleanup.add("compose state reset", _reset_state, bundle)
    cleanup.add("compose uninstall", _uninstall, bundle)
    install = run(["sudo", "scripts/install.sh", "--eval"], cwd=bundle, timeout=3600)
    assert install.exit_code == 0, install.output
    stack = _stack(bundle)
    services = set(stack["services"])
    assert CORE_SERVICES <= services and services & DATABASE_SERVICES, (
        f"unexpected service set: {sorted(services)}"
    )
    status = _service_status(bundle)
    assert set(status) == services, f"services missing from compose ps: {sorted(services - set(status))}"
    assert all(state == "running" and health == "healthy" for state, health in status.values()), (
        f"unhealthy services: {status}"
    )
    _, entry_status = curl_request("GET", "http://127.0.0.1:8080/")
    assert entry_status == "200", "public entry on 8080 is not reachable"
    token = get_admin_token("http://127.0.0.1:8080", _admin_password(bundle), evidence_stem="offline-compose-001")
    assert token.changed, (
        "first boot did not force the password change (expected 403 Password change required): "
        f"{token.status} {token.body}"
    )
    assert token.status == "200", f"{token.status} {token.body}"
    assert TOKEN_FIELDS <= token.payload.keys(), token.body
    uninstall = _uninstall(bundle)
    assert uninstall.exit_code == 0, uninstall.output
    containers = run(
        ["sudo", "docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={stack['name']}",
         "--format", "{{.Names}}"],
        timeout=120,
    )
    assert containers.exit_code == 0, containers.output
    assert not containers.stdout.strip(), f"containers of project {stack['name']} still exist: {containers.stdout}"
    assert _reset_state(bundle).exit_code == 0, "compose state reset after the case failed"
