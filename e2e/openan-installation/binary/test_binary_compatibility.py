import pathlib
import re

import pytest

from utils.binary_install import host_runtimes, install_binary, uninstall_binary, wait_registry_up
from utils.binary_offline import install_binary_offline, offline_dir, uninstall_binary_offline
from utils.env import install_config
from utils.shell import run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.full,
]

DEBIAN_PYTHON = r"\[OK\] Python [^\n]*installed (via apt|via deadsnakes PPA|\(standalone\))"
CENTOS_PYTHON = r"\[OK\] Python [^\n]*installed (via dnf|via yum|via dnf module|via yum module|\(standalone\))"
DEBIAN_NODE = r"\[OK\] Node\.js [^\n]*installed (via apt|via NodeSource)"
CENTOS_NODE = r"\[OK\] Node\.js [^\n]*installed (via dnf|via yum|via NodeSource)"
STANDALONE_NODE = r"\[OK\] Node\.js [^\n]*installed \(prebuilt\)"
DEBIAN_IDS = ("debian", "ubuntu")
CENTOS_IDS = ("centos", "rhel", "rocky", "almalinux", "fedora", "amzn", "openeuler")


def _distro_family() -> str:
    fields = {}
    for line in pathlib.Path("/etc/os-release").read_text(encoding="utf-8", errors="replace").splitlines():
        key, _, value = line.partition("=")
        fields[key.strip()] = value.strip().strip('"').lower()
    lowered = " ".join((fields.get("ID", ""), fields.get("ID_LIKE", "")))
    if any(token in lowered for token in DEBIAN_IDS):
        return "debian"
    if any(token in lowered for token in CENTOS_IDS):
        return "centos"
    return "unknown"


def _require_fresh_vm(cfg, case: str) -> None:
    if not cfg.fresh_vm:
        pytest.skip(f"OPENAN_INSTALL_FRESH_VM is not set to 1 ({case} lets the installer change the host's runtimes)")


def _runtime_paths(family: str, host: dict) -> list[tuple[str, str, str]]:
    auto_install = f"{family}-family auto-install"
    if host["python"]:
        command, version = host["python"]
        python = ("existing-interpreter", rf"\[OK\] Python {re.escape(version)} \({re.escape(command)}\)")
    else:
        python = (auto_install, DEBIAN_PYTHON if family == "debian" else CENTOS_PYTHON)
    node_install = f"{DEBIAN_NODE if family == 'debian' else CENTOS_NODE}|{STANDALONE_NODE}"
    if host["node"]:
        node = ("existing-runtime", rf"(?m)^[ \t]*\[OK\] Node\.js v{re.escape(host['node'])}[ \t\r]*$")
    else:
        node = (auto_install, node_install)
    return [("Python", *python), ("Node.js", *node)]


@getattr(pytest.mark, "DFX-openan-installation-compatibility-002")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
@pytest.mark.online
def test_runtime_auto_install_adapts_to_distro_family(require_profile, require_opt_in, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    _require_fresh_vm(cfg, "compatibility-002")
    family = _distro_family()
    if family == "unknown":
        pytest.skip("/etc/os-release is neither a Debian nor a CentOS family distribution")
    host = host_runtimes()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, evidence_stem="compatibility-002")
    assert install.exit_code == 0, install.output
    for runtime, path, pattern in _runtime_paths(family, host):
        assert re.search(pattern, install.output), (
            f"the installer did not take the {path} path for {runtime} (host runtimes before install: {host}):\n"
            f"{install.output[-2500:]}"
        )
    wait_registry_up()
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output


@getattr(pytest.mark, "DFX-openan-installation-compatibility-003")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
@pytest.mark.offline
def test_binary_offline_package_selects_wheels_by_host_architecture(require_profile, require_opt_in, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    _require_fresh_vm(cfg, "compatibility-003")
    directory = offline_dir(cfg)
    raw = run(["uname", "-m"], timeout=60).stdout.strip()
    arch = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}.get(raw)
    if arch is None:
        pytest.skip(f"unsupported host architecture {raw!r}")
    cleanup.add("binary offline uninstall", uninstall_binary_offline, directory)
    install = install_binary_offline(directory, "--reg", evidence_stem="compatibility-003")
    assert install.exit_code == 0, install.output
    assert f"Detected: {raw} \u2192 {arch}" in install.output, install.output[-2500:]
    assert re.search(rf"registry-center: \d+ wheels \({arch} confirmed\)", install.output), install.output[-2500:]
    wheel = re.search(rf"vendor/wheels/[^\s]*manylinux[^\s]*_{arch}[^\s]*\.whl", install.output)
    assert wheel, f"the install log does not show a {arch} wheel being installed:\n{install.output[-2500:]}"
    wait_registry_up()
    uninstall = uninstall_binary_offline(directory)
    assert uninstall.exit_code == 0, uninstall.output
