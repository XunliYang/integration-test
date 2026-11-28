import shutil
from pathlib import Path

import pytest

from utils.compose_install import (
    SENTINEL,
    check_compose_env,
    compose_services,
    container_env,
    container_names,
    container_port_bindings,
    install_compose,
    prepare_compose_config,
    reset_compose_state,
    runtime_file_mtime,
    set_config_value,
    set_runtime_value,
    uninstall_compose,
)
from utils.env import install_config
from utils.shell import run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.full,
]

HOSTILE_PASSWORD = "$(touch /tmp/openan-inject-check)"


def _bundle(cfg) -> Path:
    if not cfg.offline_compose_bundle:
        pytest.skip("OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE is not set")
    return Path(cfg.offline_compose_bundle)


def _healthy_text(bundle: Path) -> None:
    ps = run(["sudo", "docker", "compose", "-f", "runtime/compose.json", "ps"], cwd=bundle, timeout=300)
    assert ps.exit_code == 0 and "healthy" in ps.stdout, ps.output
    assert "unhealthy" not in ps.stdout and "exited" not in ps.stdout, ps.output


def _tcp_open(host: str, port: int, via: str = "") -> bool:
    probe = f"timeout 3 bash -c '</dev/tcp/{host}/{port}'"
    command = ["ssh", "-o", "BatchMode=yes", via, probe] if via else ["bash", "-c", probe]
    return run(command, timeout=30).exit_code == 0


@getattr(pytest.mark, "DFX-openan-installation-security-006")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P1
def test_compose_config_parser_rejects_injection_attempts_and_managed_key_override(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = _bundle(cfg)
    assert not Path(SENTINEL).exists(), f"{SENTINEL} exists before the test"
    config = prepare_compose_config(stem="security-006", registry_db_password=f"'{HOSTILE_PASSWORD}'")
    cleanup.add("delete generated config", shutil.rmtree, config.directory, ignore_errors=True)
    cleanup.add("compose state reset", reset_compose_state, bundle)
    cleanup.add("compose uninstall", uninstall_compose, bundle)
    install = install_compose(bundle, config, evidence_stem="security-006-install")
    assert install.exit_code == 0, install.output
    _healthy_text(bundle)
    assert not Path(SENTINEL).exists(), "the hostile password value was executed"
    registry = next(name for name in container_names(bundle) if "registry-center" in name)
    assert container_env(registry, "DB_PASSWORD") == HOSTILE_PASSWORD, "the literal password did not reach the container"
    set_runtime_value(config, "registry", "REGISTRY_PORT", "5000")
    before = runtime_file_mtime(bundle, "compose.json")
    managed = check_compose_env(bundle, config)
    assert managed.exit_code != 0, "a runtime env file overriding a managed key was accepted"
    assert "REGISTRY runtime env overrides managed keys: REGISTRY_PORT" in managed.stderr, managed.output
    assert runtime_file_mtime(bundle, "compose.json") == before, "runtime/compose.json was regenerated"
    set_runtime_value(config, "registry", "REGISTRY_PORT", None)
    set_config_value(config, "E2E_UNKNOWN_KEY", "1")
    unknown = check_compose_env(bundle, config)
    assert unknown.exit_code != 0, "an unknown config.env key was accepted"
    assert "Unknown deployment keys: E2E_UNKNOWN_KEY" in unknown.stderr, unknown.output
    assert runtime_file_mtime(bundle, "compose.json") == before, "runtime/compose.json was regenerated"
    uninstall = uninstall_compose(bundle)
    assert uninstall.exit_code == 0 and container_names(bundle) == []
    assert reset_compose_state(bundle).exit_code == 0
    shutil.rmtree(config.directory, ignore_errors=True)
    assert not config.directory.exists() and not Path(SENTINEL).exists()


@getattr(pytest.mark, "DFX-openan-installation-security-005")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
def test_compose_stack_publishes_only_the_public_entry(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = _bundle(cfg)
    config = prepare_compose_config(stem="security-005")
    cleanup.add("delete generated config", shutil.rmtree, config.directory, ignore_errors=True)
    cleanup.add("compose state reset", reset_compose_state, bundle)
    cleanup.add("compose uninstall", uninstall_compose, bundle)
    install = install_compose(bundle, config, evidence_stem="security-005-install")
    assert install.exit_code == 0, install.output
    services = compose_services(bundle)["services"]
    publishing = {name for name, service in services.items() if service.get("ports")}
    assert publishing == {"openan-nginx"}, f"services publishing host ports: {sorted(publishing)}"
    assert any(str(port).startswith("0.0.0.0:8080:") for port in services["openan-nginx"]["ports"]), services["openan-nginx"]["ports"]
    containers = container_names(bundle)
    assert containers, "no containers of the compose project are running"
    for container in containers:
        expected = {"80": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]} if "nginx" in container else {}
        assert container_port_bindings(container) == expected, f"unexpected port bindings on {container}"
    host_ip = run(["hostname", "-I"], timeout=60).stdout.split()[0]
    db_port = 5432 if config.database == "postgresql" else 3306
    for port in (5000, 5001, db_port):
        assert not _tcp_open(host_ip, port), f"port {port} is reachable on the host address {host_ip}"
        if cfg.probe_host:
            assert not _tcp_open(host_ip, port, via=cfg.probe_host), (
                f"port {port} on {host_ip} is reachable from the adjacent machine {cfg.probe_host}"
            )
    uninstall = uninstall_compose(bundle)
    assert uninstall.exit_code == 0 and container_names(bundle) == []
    assert reset_compose_state(bundle).exit_code == 0
