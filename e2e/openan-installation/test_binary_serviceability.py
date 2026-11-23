import pathlib

import pytest

from utils.env import install_config
from utils.shell import file_sha256, http_status, port_listening, run, run_interactive, wait_until

# The binary registry-center has no /health route; its FastAPI app only exposes
# /rest/v1/registry-center/* (openapi/docs disabled). The query endpoint returns
# 200 with an empty list when the service is up and reachable.
REGISTRY_UP = "http://127.0.0.1:5000/rest/v1/registry-center/agent-cards"


def _wait_registry_up(timeout: int = 120):
    # The install script backgrounds uvicorn and exits before it is listening;
    # poll until the query endpoint answers 200.
    assert wait_until(lambda: http_status(REGISTRY_UP) == "200", timeout=timeout), REGISTRY_UP

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
    # The install script backgrounds the services and exits before they bind;
    # wait until the data-plane ports are listening so a subsequent uninstall
    # can find and kill them (otherwise its port scan skips them).
    assert wait_until(lambda: port_listening(5000) and port_listening(5001), timeout=120), (
        "services did not start listening within 120s of install"
    )


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
    _wait_registry_up()
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
    # Services were confirmed listening before uninstall; all 14 ports must be
    # released. Agents share one process (samples.start_agents_server listens on
    # 8080 + 8899-8907/26335/26336), so they die together — assert each port.
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
    for name, argv in TOOL_COMMANDS.items():
        result = run(argv, timeout=60)
        assert result.exit_code == 0, f"environment tool {name} is not preserved: {result.output}"
