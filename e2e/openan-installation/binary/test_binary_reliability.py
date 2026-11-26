import re
import subprocess
import sys

import pytest

from utils.binary_install import install_binary, uninstall_binary, wait_registry_up
from utils.env import install_config
from utils.shell import http_status, listening_pids, process_cmdline, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.P1,
    pytest.mark.full,
]

CONFLICT_PORT = 5000


def _start_placeholder() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "http.server", str(CONFLICT_PORT), "--bind", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@getattr(pytest.mark, "DFX-openan-installation-reliability-003")
@getattr(pytest.mark, "26-winter")
def test_port_conflict_is_detected_and_cleared_before_service_start(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    placeholder = _start_placeholder()
    cleanup.add("stop placeholder", placeholder.kill)
    assert wait_until(lambda: bool(listening_pids(CONFLICT_PORT)), timeout=30), (
        "the placeholder did not start listening on port 5000"
    )
    placeholder_pid = str(placeholder.pid)
    assert placeholder_pid in listening_pids(CONFLICT_PORT)
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, evidence_stem="reliability-003")
    assert install.exit_code == 0, install.output
    assert re.search(r"Port 5000 is in use, killing PID\(s\):\s*\d+", install.output), install.output[-2000:]
    wait_registry_up()
    assert placeholder.poll() is not None, "the placeholder still owns port 5000"
    owners = listening_pids(CONFLICT_PORT)
    assert owners and placeholder_pid not in owners, f"port 5000 owners after install: {sorted(owners)}"
    for pid in owners:
        assert "agent_registry.start" in process_cmdline(pid), f"port 5000 is owned by an unexpected process {pid}"
    assert http_status(f"http://127.0.0.1:{CONFLICT_PORT}/rest/v1/registry-center/agent-cards") == "200"
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
