import pathlib
import re

import pytest

from utils.binary_install import (
    SAMPLE_AGENTS_PORTS,
    UNINSTALL_PORTS,
    install_binary,
    uninstall_binary,
    wait_registry_up,
)
from utils.env import install_config
from utils.shell import port_listening, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.full,
]


def _release_ports() -> None:
    for port in UNINSTALL_PORTS:
        assert wait_until(lambda p=port: not port_listening(p), timeout=60), f"port {port} still listening after uninstall"


@getattr(pytest.mark, "FIT-openan-installation-binary-sample-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
def test_sample_flag_starts_agents_example_server(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, "--sample", evidence_stem="binary-sample-001")
    assert install.exit_code == 0, install.output
    assert "agents examples server:" in install.output, install.output[-1500:]
    assert wait_until(lambda: all(port_listening(port) for port in SAMPLE_AGENTS_PORTS), timeout=120), (
        "the sample agents server did not open its ports (8899-8907, 26335, 26336)"
    )
    nginx_conf = pathlib.Path("/etc/nginx/conf.d/openan.conf").read_text(encoding="utf-8")
    assert "8080" not in nginx_conf, "nginx exposes the sample agents server on 8080"
    assert "root /var/www/openan;" in nginx_conf, "nginx does not serve the frontend static assets"
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    _release_ports()


@getattr(pytest.mark, "FIT-openan-installation-binary-version-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
def test_version_flag_pins_component_source_tag(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    if not cfg.reg_version:
        pytest.skip("OPENAN_INSTALL_REG_VERSION is not set")
    version = cfg.reg_version if cfg.reg_version.startswith("v") else f"v{cfg.reg_version}"
    if version == "v1.0.0":
        pytest.skip("OPENAN_INSTALL_REG_VERSION equals the built-in default v1.0.0; a different tag is needed")
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, "--reg", "--reg-version", cfg.reg_version, evidence_stem="binary-version-001")
    assert install.exit_code == 0, install.output
    assert re.search(rf"registry-center:\s+{re.escape(version)} \(flag\)", install.output), install.output[-2500:]
    assert f"archive/refs/tags/{version}.tar.gz" in install.output, "the download source is not the pinned release archive"
    assert "on disk is" not in install.output and "already exists, skipping download" not in install.output, (
        "the pinned tag was not freshly downloaded"
    )
    marker = cfg.binary_dir / "registry-center" / ".source-version"
    assert marker.read_text(encoding="utf-8").strip() == version, f"{marker} does not record {version}"
    wait_registry_up()
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
