import shutil
from pathlib import Path

import pytest

from utils.compose_install import (
    CORE_SERVICES,
    GENERATED_FILES,
    check_compose_env,
    compose_project,
    container_names,
    install_compose,
    prepare_compose_config,
    reset_compose_state,
    runtime_path_exists,
    service_status,
    uninstall_compose,
    volume_created_at,
)
from utils.env import install_config
from utils.shell import run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.full,
]


def _bundle(cfg) -> Path:
    if not cfg.offline_compose_bundle:
        pytest.skip("OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE is not set")
    return Path(cfg.offline_compose_bundle)


def _healthy(bundle: Path) -> None:
    status = service_status(bundle)
    assert set(status) >= CORE_SERVICES, f"services missing from compose ps: {sorted(status)}"
    assert all(state == "running" and health == "healthy" for state, health in status.values()), (
        f"unhealthy services: {status}"
    )


@getattr(pytest.mark, "DFX-openan-installation-serviceability-006")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P1
def test_compose_uninstall_keeps_data_volumes_for_reinstall_reuse(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = _bundle(cfg)
    config = prepare_compose_config(stem="serviceability-006")
    cleanup.add("delete generated config", shutil.rmtree, config.directory, ignore_errors=True)
    cleanup.add("compose state reset", reset_compose_state, bundle)
    cleanup.add("compose uninstall", uninstall_compose, bundle)
    install = install_compose(bundle, config, evidence_stem="serviceability-006-install")
    assert install.exit_code == 0, install.output
    _healthy(bundle)
    project = compose_project(bundle)
    assert project == config.project, project
    created = volume_created_at(config.volume)
    uninstall = uninstall_compose(bundle)
    assert uninstall.exit_code == 0, uninstall.output
    assert container_names(bundle) == [], "containers survived the uninstall"
    assert volume_created_at(config.volume) == created, "the SQL volume did not survive the uninstall"
    assert runtime_path_exists(bundle, "compose.json"), "runtime/compose.json did not survive the uninstall"
    assert runtime_path_exists(bundle, "registry-center/data"), "application data did not survive the uninstall"
    reinstall = install_compose(bundle, config, evidence_stem="serviceability-006-reinstall")
    assert reinstall.exit_code == 0, reinstall.output
    _healthy(bundle)
    assert volume_created_at(config.volume) == created, "the reinstall did not reuse the retained volume"
    final = uninstall_compose(bundle)
    assert final.exit_code == 0 and container_names(bundle) == []
    assert reset_compose_state(bundle).exit_code == 0, "compose state reset after the case failed"


@getattr(pytest.mark, "FIT-openan-installation-compose-db-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
def test_compose_database_type_postgresql_selects_bundled_postgres(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = _bundle(cfg)
    cleanup.add("compose state reset", reset_compose_state, bundle)
    cleanup.add("compose uninstall", uninstall_compose, bundle)
    generated = run(["sudo", "scripts/gen-secrets.sh", "--eval"], cwd=bundle, timeout=600)
    assert generated.exit_code == 0, f"gen-secrets.sh --eval failed:\n{generated.output}"
    for name in GENERATED_FILES:
        assert (bundle / name).is_file(), f"gen-secrets.sh did not produce {name}"
    config = prepare_compose_config("postgresql", stem="compose-db-001", generated_dir=bundle)
    cleanup.add("delete generated config", shutil.rmtree, config.directory, ignore_errors=True)
    check = check_compose_env(bundle, config)
    assert check.exit_code == 0, check.output
    install = install_compose(bundle, config, evidence_stem="compose-db-001")
    assert install.exit_code == 0, install.output
    _healthy(bundle)
    assert "openan-postgres" in service_status(bundle), service_status(bundle)
    uninstall = uninstall_compose(bundle)
    assert uninstall.exit_code == 0 and container_names(bundle) == []
    assert reset_compose_state(bundle).exit_code == 0
