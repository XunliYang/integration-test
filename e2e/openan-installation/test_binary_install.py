import pytest

from utils.env import install_config
from utils.shell import http_status, port_listening, run, run_interactive, wait_until

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


def test_one_click_install_full_stack_ready(require_profile):
    require_profile("online-vm")
    cfg = install_config()
    install = run_interactive("./install.sh", cwd=cfg.binary_dir, answers=LLM_SKIP, evidence_stem="binary-install-001")
    assert install.exit_code == 0, install.output
    assert "pid" in install.output.lower(), install.output
    _wait_registry_up()
    assert http_status("https://127.0.0.1/") == "200"
    # nginx proxies /registry/ -> registry:5000/ and /api/orchestrate/ -> oc:5001/,
    # but neither backend serves a root route; the reachable endpoints are the
    # registry query API and the orchestration templates list.
    assert http_status("https://127.0.0.1/registry/rest/v1/registry-center/agent-cards") == "200"
    assert http_status("https://127.0.0.1/api/orchestrate/rest/v1/orchestrate/templates") == "200"
    uninstall = run("./uninstall.sh --force", cwd=cfg.binary_dir, timeout=600)
    assert uninstall.exit_code == 0, uninstall.output
    assert not port_listening(5000)
    assert not port_listening(5001)
    assert not port_listening(443)
    assert not (cfg.binary_dir / "registry-center").exists()
    assert not (cfg.binary_dir / "orchestration-center").exists()


def test_reg_only_install_deploys_registry_center_alone(require_profile):
    require_profile("online-vm")
    cfg = install_config()
    install = run_interactive("./install.sh --reg", cwd=cfg.binary_dir, answers=LLM_SKIP, evidence_stem="binary-components-001")
    assert install.exit_code == 0, install.output
    _wait_registry_up()
    assert not port_listening(5001)
    assert not port_listening(443)
    assert not (cfg.binary_dir / "orchestration-center").exists()
    uninstall = run("./uninstall.sh --force", cwd=cfg.binary_dir, timeout=600)
    assert uninstall.exit_code == 0, uninstall.output
    assert not port_listening(5000)
