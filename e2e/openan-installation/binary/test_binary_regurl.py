import pytest

from utils.binary_install import (
    ORCHESTRATION_UP,
    binary_answers,
    install_binary,
    uninstall_binary,
    wait_orchestration_up,
)
from utils.env import install_config
from utils.shell import config_value, http_status

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.full,
]


@getattr(pytest.mark, "FIT-openan-installation-binary-regurl-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P1
def test_orchestration_only_writes_registry_url_as_is(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    if not cfg.registry_url:
        pytest.skip("OPENAN_INSTALL_REGISTRY_URL is not set")
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(
        cfg,
        "--orc",
        answers=binary_answers(registry_url=cfg.registry_url),
        evidence_stem="binary-regurl-001",
    )
    assert install.exit_code == 0, install.output
    assert f"[OK] server.conf agent_registry_url set to {cfg.registry_url}." in install.output, install.output[-2000:]
    server_conf = cfg.binary_dir / "orchestration-center" / "etc" / "conf" / "server.conf"
    assert config_value(server_conf, "agent_registry_url") == cfg.registry_url, (
        f"agent_registry_url in {server_conf} is not the value entered at the prompt"
    )
    wait_orchestration_up()
    assert http_status(ORCHESTRATION_UP) == "200"
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output


@getattr(pytest.mark, "FIT-openan-installation-binary-regurl-002")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
def test_full_stack_mode_writes_local_registry_url_as_http(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, evidence_stem="binary-regurl-002")
    assert install.exit_code == 0, install.output
    server_conf = cfg.binary_dir / "orchestration-center" / "etc" / "conf" / "server.conf"
    assert config_value(server_conf, "agent_registry_url") == "http://127.0.0.1:5000", (
        f"agent_registry_url in {server_conf} is not the local HTTP registry address"
    )
    wait_orchestration_up()
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
