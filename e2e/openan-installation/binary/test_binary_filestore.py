import pytest

from utils.agentcard import delete_card, fetch_card, make_sample_agent_card, register_card
from utils.binary_install import REGISTRY_BASE, install_binary, uninstall_binary, wait_registry_up
from utils.env import install_config
from utils.shell import config_value

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    getattr(pytest.mark, "registry-center"),
    pytest.mark.P1,
    pytest.mark.full,
]


@getattr(pytest.mark, "FIT-openan-installation-binary-filestore-001")
@getattr(pytest.mark, "26-winter")
def test_binary_install_defaults_registry_center_to_file_persistence(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, "--reg", evidence_stem="binary-filestore-001")
    assert install.exit_code == 0, install.output
    wait_registry_up()
    persistence_conf = cfg.binary_dir / "registry-center" / "etc" / "conf" / "persistence.conf"
    assert config_value(persistence_conf, "persistence.mode") == "file", (
        f"{persistence_conf} does not select file storage"
    )
    card = make_sample_agent_card()
    body, status = register_card(REGISTRY_BASE, card)
    assert status == "201", f"agent registration failed: {status} {body}"
    body, status = fetch_card(REGISTRY_BASE, card)
    assert status == "200" and card["name"] in body, f"agent query failed: {status} {body}"
    body, status = delete_card(REGISTRY_BASE, card)
    assert status == "200", f"agent deletion failed: {status} {body}"
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    assert not (cfg.binary_dir / "registry-center").exists()
