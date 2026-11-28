import os
import pathlib
import shutil

import pytest

from utils.binary_install import (
    SAMPLE_AGENTS_PORTS,
    SAMPLE_ANSWERS,
    UNINSTALL_PORTS,
    install_binary,
    uninstall_binary,
    wait_orchestration_up,
    wait_registry_up,
)
from utils.env import install_config
from utils.shell import file_sha256, http_status, port_listening, run, run_interactive, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
]

TOOL_COMMANDS = (
    ("python3", "--version", (".python3.12/python/bin/python3",)),
    ("node", "-v", (".node/bin/node",)),
    ("nginx", "-v", ("/usr/sbin/nginx", "/sbin/nginx")),
)


def _resolve_tool(name: str, *fallbacks: pathlib.Path) -> str:
    found = shutil.which(name)
    if found:
        return found
    for candidate in fallbacks:
        if os.access(candidate, os.X_OK):
            return str(candidate)
    pytest.fail(f"environment tool {name} is not on PATH and not found in {[str(item) for item in fallbacks]}")


def _install_full_stack(cfg, *, start_sample: bool = False) -> str:
    install = install_binary(cfg, answers=SAMPLE_ANSWERS if start_sample else None)
    assert install.exit_code == 0, install.output
    # The install script backgrounds the services and exits before they bind;
    # wait until the data-plane ports are listening so a subsequent uninstall
    # can find and kill them (otherwise its port scan skips them).
    assert wait_until(lambda: port_listening(5000) and port_listening(5001), timeout=120), (
        "services did not start listening within 120s of install"
    )
    return install.output


@getattr(pytest.mark, "DFX-openan-installation-serviceability-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P0
@pytest.mark.smoke
def test_binary_rerun_keeps_certificates_idempotent(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    _install_full_stack(cfg)
    cert_paths = ["/etc/nginx/ssl/cert.pem", "/etc/nginx/ssl/key.pem"]
    registry_ssl = cfg.binary_dir / "registry-center" / "etc" / "ssl"
    assert registry_ssl.is_dir(), f"registry-center TLS directory not found: {registry_ssl}"
    cert_paths += [str(item) for item in sorted(registry_ssl.glob("*")) if item.is_file()]
    hashes_before = {path: file_sha256(path) for path in cert_paths}
    rerun = install_binary(cfg, evidence_stem="serviceability-001")
    assert rerun.exit_code == 0, rerun.output
    wait_registry_up()
    hashes_after = {path: file_sha256(path) for path in cert_paths}
    assert hashes_after == hashes_before, f"certificate files changed after re-run: {cert_paths}"
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output


@getattr(pytest.mark, "DFX-openan-installation-serviceability-003")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P0
@pytest.mark.smoke
def test_uninstall_force_removes_artifacts_keeps_tools(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    output = _install_full_stack(cfg, start_sample=True)
    assert "agents examples server:" in output, f"sample agents server was not started:\n{output[-1500:]}"
    assert wait_until(lambda: all(port_listening(port) for port in SAMPLE_AGENTS_PORTS), timeout=120), (
        "sample agents server did not open all of its ports (8899-8907, 26335, 26336)"
    )
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    # Services were confirmed listening before uninstall; all 14 ports must be
    # released. Agents share one process (samples.start_agents_server listens on
    # 8899-8907/26335/26336; 8080 is only scanned by uninstall.sh), so they die
    # together — assert each port.
    for port in UNINSTALL_PORTS:
        assert wait_until(lambda p=port: not port_listening(p), timeout=60), (
            f"port {port} still listening after uninstall"
        )
    assert not pathlib.Path("/etc/nginx/conf.d/openan.conf").exists()
    # uninstall removes the cert files but leaves the (now empty) ssl dir;
    # assert it is gone OR contains nothing.
    ssl_dir = pathlib.Path("/etc/nginx/ssl")
    assert not ssl_dir.exists() or not any(ssl_dir.iterdir()), (
        f"unexpected leftover under /etc/nginx/ssl: {list(ssl_dir.iterdir())}"
    )
    assert not (cfg.binary_dir / "registry-center").exists()
    assert not (cfg.binary_dir / "orchestration-center").exists()
    for name, argument, fallbacks in TOOL_COMMANDS:
        result = run([_resolve_tool(name, *fallbacks), argument], timeout=60)
        assert result.exit_code == 0, f"environment tool {name} is not preserved: {result.output}"


@getattr(pytest.mark, "DFX-openan-installation-serviceability-004")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
@pytest.mark.full
def test_interactive_uninstall_shows_plan_and_cancels_without_changes(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    _install_full_stack(cfg)
    cancel = run_interactive(
        "./uninstall.sh",
        cwd=cfg.binary_dir,
        answers=[(r"Proceed with uninstallation\? \[y/N\]: ", "n")],
        evidence_stem="serviceability-004",
    )
    assert cancel.exit_code == 0, cancel.output
    for section in ("OpenAN Uninstallation Plan", "Processes to kill:", "kill PID", "Nginx to stop/clean:",
                    "Directories to delete:", "will be PRESERVED"):
        assert section in cancel.output, f"{section!r} missing from the uninstall plan:\n{cancel.output[-2000:]}"
    assert "[CANCEL] Uninstallation aborted." in cancel.output, cancel.output[-2000:]
    wait_registry_up()
    wait_orchestration_up()
    assert http_status("https://127.0.0.1/") == "200", "nginx entry stopped after the cancelled uninstall"
    assert pathlib.Path("/etc/nginx/conf.d/openan.conf").is_file(), "nginx config removed after the cancelled uninstall"
    assert (cfg.binary_dir / "registry-center").is_dir(), "project directory removed after the cancelled uninstall"
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
