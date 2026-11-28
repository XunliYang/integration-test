import re

import pytest

from utils.binary_install import install_binary, uninstall_binary, wait_registry_up
from utils.env import install_config
from utils.shell import http_status, port_listening

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.P0,
    pytest.mark.smoke,
]

SUMMARY_PIDS = (
    r"registry-center:\s+http://127\.0\.0\.1:5000\s+\(PID: \d+\)",
    r"orchestration backend:\s+http://127\.0\.0\.1:5001\s+\(PID: \d+\)",
    r"nginx \(HTTPS\):\s+https://\S+\s+\(PID: \d+\)",
)


@getattr(pytest.mark, "FIT-openan-installation-binary-install-001")
@getattr(pytest.mark, "26-winter")
def test_one_click_install_full_stack_ready(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, evidence_stem="binary-install-001")
    assert install.exit_code == 0, install.output
    for service in SUMMARY_PIDS:
        assert re.search(service, install.output), (
            f"install summary lacks the PID/URL line {service!r}:\n{install.output[-1500:]}"
        )
    assert "agents examples server:" not in install.output, (
        "sample agents server started although --sample was not given"
    )
    wait_registry_up()
    assert http_status("https://127.0.0.1/") == "200"
    # nginx proxies /registry/ -> registry:5000/ and /api/orchestrate/ -> oc:5001/,
    # but neither backend serves a root route; the reachable endpoints are the
    # registry query API and the orchestration templates list.
    assert http_status("https://127.0.0.1/registry/rest/v1/registry-center/agent-cards") == "200"
    assert http_status("https://127.0.0.1/api/orchestrate/rest/v1/orchestrate/templates") == "200"
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    assert not port_listening(5000)
    assert not port_listening(5001)
    assert not port_listening(443)
    assert not (cfg.binary_dir / "registry-center").exists()
    assert not (cfg.binary_dir / "orchestration-center").exists()


@getattr(pytest.mark, "FIT-openan-installation-binary-components-001")
@getattr(pytest.mark, "26-winter")
def test_reg_only_install_deploys_registry_center_alone(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, "--reg", evidence_stem="binary-components-001")
    assert install.exit_code == 0, install.output
    wait_registry_up()
    assert not port_listening(5001)
    assert not port_listening(443)
    assert not (cfg.binary_dir / "orchestration-center").exists()
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    assert not port_listening(5000)
