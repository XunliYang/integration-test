import re

import pytest

from utils.binary_install import install_binary, uninstall_binary
from utils.env import install_config
from utils.shell import process_cmdline, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.P1,
    pytest.mark.full,
]

SUMMARY_SERVICES = (
    (r"registry-center:\s+http://127\.0\.0\.1:5000\s+\(PID: (\d+)\)", "agent_registry.start"),
    (r"orchestration backend:\s+http://127\.0\.0\.1:5001\s+\(PID: (\d+)\)", "orchestrate.start"),
    (r"nginx \(HTTPS\):\s+https://\S+\s+\(PID: (\d+)\)", "nginx: master"),
)


@getattr(pytest.mark, "DFX-openan-installation-testability-002")
@getattr(pytest.mark, "26-winter")
def test_binary_install_exposes_pids_and_logs_for_external_state_identification(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, evidence_stem="testability-002")
    assert install.exit_code == 0, install.output
    pids = []
    for pattern, process in SUMMARY_SERVICES:
        match = re.search(pattern, install.output)
        assert match, f"install summary lacks a PID line for {pattern!r}:\n{install.output[-1500:]}"
        cmdline = process_cmdline(match.group(1))
        assert process in cmdline, f"PID {match.group(1)} is not a {process} process: {cmdline!r}"
        pids.append(match.group(1))
    assert "agents examples server:" not in install.output, install.output[-1500:]
    assert f"To stop all: kill {pids[0]} {pids[1]}" in install.output, install.output[-1500:]
    logs = [cfg.binary_dir / "registry-center" / "registry-center.log",
            cfg.binary_dir / "orchestration-center" / "backend.log"]
    assert wait_until(
        lambda: all(path.is_file() and path.stat().st_size > 0 for path in logs), timeout=120
    ), [f"{path} missing or empty" for path in logs if not path.is_file() or path.stat().st_size == 0]
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
