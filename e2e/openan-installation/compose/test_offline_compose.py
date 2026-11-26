from pathlib import Path

import pytest

from utils.compose_install import (
    CORE_SERVICES,
    DATABASE_SERVICES,
    admin_password,
    compose_services,
    container_names,
    reset_compose_state,
    service_status,
    uninstall_compose,
)
from utils.env import install_config
from utils.oc_auth import TOKEN_FIELDS, get_admin_token
from utils.shell import curl_request, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    getattr(pytest.mark, "registry-center"),
    getattr(pytest.mark, "orchestration-center"),
    pytest.mark.P0,
    pytest.mark.smoke,
]


def run_eval(bundle: Path):
    # scripts/install.sh --eval is the case's own entry even though it is
    # currently broken in the product (see README, Known Product Defects #2)
    return run(["sudo", "scripts/install.sh", "--eval"], cwd=bundle, timeout=3600)


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
    cleanup.add("compose state reset", reset_compose_state, bundle)
    cleanup.add("compose uninstall", uninstall_compose, bundle)
    install = run_eval(bundle)
    assert install.exit_code == 0, install.output
    stack = compose_services(bundle)
    services = set(stack["services"])
    assert CORE_SERVICES <= services and services & DATABASE_SERVICES, (
        f"unexpected service set: {sorted(services)}"
    )
    status = service_status(bundle)
    assert set(status) == services, f"services missing from compose ps: {sorted(services - set(status))}"
    assert all(state == "running" and health == "healthy" for state, health in status.values()), (
        f"unhealthy services: {status}"
    )
    _, entry_status = curl_request("GET", "http://127.0.0.1:8080/")
    assert entry_status == "200", "public entry on 8080 is not reachable"
    token = get_admin_token("http://127.0.0.1:8080", admin_password(bundle), evidence_stem="offline-compose-001")
    assert token.changed, (
        "first boot did not force the password change (expected 403 Password change required): "
        f"{token.status} {token.body}"
    )
    assert token.status == "200", f"{token.status} {token.body}"
    assert TOKEN_FIELDS <= token.payload.keys(), token.body
    uninstall = uninstall_compose(bundle)
    assert uninstall.exit_code == 0, uninstall.output
    assert container_names(bundle) == [], f"containers of project {stack['name']} still exist"
    assert reset_compose_state(bundle).exit_code == 0, "compose state reset after the case failed"
