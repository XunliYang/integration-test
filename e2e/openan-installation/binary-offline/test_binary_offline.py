import pathlib
import shutil

import pytest

from utils.binary_install import UNINSTALL_PORTS, wait_registry_up
from utils.binary_offline import component_dirs, install_binary_offline, offline_dir, uninstall_binary_offline
from utils.env import install_config
from utils.shell import http_status, port_listening, run, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.P1,
    pytest.mark.full,
]

TOOLS = (("python3", "--version"), ("node", "-v"), ("nginx", "-v"))
TOOL_FALLBACKS = {
    "python3": (".python3.12/python/bin/python3",),
    "node": (".node/bin/node",),
    "nginx": ("/usr/sbin/nginx", "/sbin/nginx"),
}


def _tool_command(directory: pathlib.Path, tool: str, flag: str) -> list[str]:
    if shutil.which(tool):
        return [tool, flag]
    for candidate in TOOL_FALLBACKS[tool]:
        path = pathlib.Path(candidate) if candidate.startswith("/") else directory / candidate
        if path.is_file():
            return [str(path), flag]
    pytest.fail(f"environment tool {tool} is not on PATH and not found in {TOOL_FALLBACKS[tool]}")


def _tool_versions(directory: pathlib.Path) -> dict[str, str]:
    versions = {}
    for tool, flag in TOOLS:
        result = run(_tool_command(directory, tool, flag), timeout=60)
        assert result.exit_code == 0, f"{tool} {flag} failed: {result.output}"
        versions[tool] = (result.stdout + result.stderr).strip()
    return versions


@getattr(pytest.mark, "FIT-openan-installation-binary-offline-001")
@getattr(pytest.mark, "26-winter")
def test_binary_offline_tarball_install_brings_services_up(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    directory = offline_dir(cfg)
    cleanup.add("binary offline uninstall", uninstall_binary_offline, directory)
    install = install_binary_offline(directory, evidence_stem="binary-offline-001")
    assert install.exit_code == 0, install.output
    wait_registry_up()
    assert http_status("https://127.0.0.1/") == "200"
    assert pathlib.Path("/var/www/openan").is_dir(), "/var/www/openan static assets are missing"
    assert pathlib.Path("/etc/nginx/conf.d/openan.conf").is_file(), "/etc/nginx/conf.d/openan.conf is missing"
    uninstall = uninstall_binary_offline(directory)
    assert uninstall.exit_code == 0, uninstall.output


@getattr(pytest.mark, "DFX-openan-installation-serviceability-008")
@getattr(pytest.mark, "26-winter")
def test_binary_offline_uninstall_removes_versioned_dirs_and_the_static_web_root(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    directory = offline_dir(cfg)
    cleanup.add("binary offline uninstall", uninstall_binary_offline, directory)
    install = install_binary_offline(directory, evidence_stem="serviceability-008")
    assert install.exit_code == 0, install.output
    wait_registry_up()
    installed = component_dirs(directory, "registry-center") + component_dirs(directory, "orchestration-center")
    assert len(installed) == 2, f"versioned project directories not found: {installed}"
    versions = _tool_versions(directory)
    assert all(value for value in versions.values()), versions
    uninstall = uninstall_binary_offline(directory)
    assert uninstall.exit_code == 0, uninstall.output
    for port in UNINSTALL_PORTS:
        assert wait_until(lambda p=port: not port_listening(p), timeout=60), f"port {port} still listening after uninstall"
    assert not pathlib.Path("/var/www/openan").exists(), "/var/www/openan was not removed"
    assert not pathlib.Path("/etc/nginx/conf.d/openan.conf").exists(), "/etc/nginx/conf.d/openan.conf was not removed"
    assert not component_dirs(directory, "registry-center") and not component_dirs(directory, "orchestration-center"), (
        "versioned project directories were not removed"
    )
    assert _tool_versions(directory) == versions, "environment tools changed after the uninstall"
