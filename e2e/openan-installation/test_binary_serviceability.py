import pathlib

import pytest

from utils.env import install_config
from utils.shell import file_sha256, http_status, port_listening, run, run_interactive

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.P0,
    pytest.mark.smoke,
]

LLM_SKIP = [(r"llm", "y")]
UNINSTALL_PORTS = [5000, 5001, 8080, 26335, 26336] + list(range(8899, 8908))
TOOL_COMMANDS = {"python3": ["python3", "--version"], "node": ["node", "-v"], "nginx": ["nginx", "-v"]}


def _install_full_stack(cfg):
    install = run_interactive("./install.sh", cwd=cfg.binary_dir, answers=LLM_SKIP)
    assert install.exit_code == 0, install.output


def test_binary_rerun_keeps_certificates_idempotent(require_profile):
    require_profile("online-vm")
    cfg = install_config()
    _install_full_stack(cfg)
    cert_paths = ["/etc/nginx/ssl/cert.pem", "/etc/nginx/ssl/key.pem"]
    registry_ssl = cfg.binary_dir / "registry-center" / "etc" / "ssl"
    if registry_ssl.is_dir():
        cert_paths += [str(item) for item in sorted(registry_ssl.glob("*")) if item.is_file()]
    hashes_before = {path: file_sha256(path) for path in cert_paths}
    rerun = run_interactive("./install.sh", cwd=cfg.binary_dir, answers=LLM_SKIP, evidence_stem="serviceability-001")
    assert rerun.exit_code == 0, rerun.output
    assert http_status("http://127.0.0.1:5000/health") == "200"
    hashes_after = {path: file_sha256(path) for path in cert_paths}
    assert hashes_after == hashes_before, f"certificate files changed after re-run: {cert_paths}"
    uninstall = run("./uninstall.sh --force", cwd=cfg.binary_dir, timeout=600)
    assert uninstall.exit_code == 0, uninstall.output


def test_uninstall_force_removes_artifacts_keeps_tools(require_profile):
    require_profile("online-vm")
    cfg = install_config()
    _install_full_stack(cfg)
    uninstall = run("./uninstall.sh --force", cwd=cfg.binary_dir, timeout=600)
    assert uninstall.exit_code == 0, uninstall.output
    for port in UNINSTALL_PORTS:
        assert not port_listening(port), f"port {port} is still listening after uninstall"
    assert not pathlib.Path("/etc/nginx/conf.d/openan.conf").exists()
    assert not pathlib.Path("/etc/nginx/ssl").exists()
    assert not (cfg.binary_dir / "registry-center").exists()
    assert not (cfg.binary_dir / "orchestration-center").exists()
    for name, argv in TOOL_COMMANDS.items():
        result = run(argv, timeout=60)
        assert result.exit_code == 0, f"environment tool {name} is not preserved: {result.output}"
