from pathlib import Path

import pytest

from utils.env import install_config
from utils.shell import curl_request, kubectl, kubectl_jsonpath, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    getattr(pytest.mark, "registry-center"),
    getattr(pytest.mark, "orchestration-center"),
    pytest.mark.P0,
    pytest.mark.smoke,
]


def test_offline_k8s_bundle_install_fully_offline(require_profile):
    require_profile("offline-node")
    cfg = install_config()
    if not cfg.offline_k8s_bundle:
        pytest.skip("OPENAN_INSTALL_OFFLINE_K8S_BUNDLE is not set")
    bundle = Path(cfg.offline_k8s_bundle)
    check = run(["sudo", "scripts/check-env.sh", "--config", cfg.offline_config_env], cwd=bundle, timeout=600)
    assert check.exit_code == 0, check.output
    assert "FAIL" not in check.stdout, check.output
    install = run(["sudo", "scripts/install.sh", "--config", cfg.offline_config_env], cwd=bundle, timeout=3600)
    assert install.exit_code == 0, install.output
    pods = kubectl(["-n", "openan", "get", "pods", "--no-headers"])
    assert pods.exit_code == 0, pods.output
    assert all("Running" in line for line in pods.stdout.splitlines() if line.strip()), pods.output
    ingress_address = kubectl_jsonpath("ingress", "{.items[*].status.loadBalancer.ingress[0].ip}").stdout.strip()
    assert ingress_address, "ingress has no ADDRESS"
    base = f"https://{ingress_address.split()[0]}"
    _, home_status = curl_request("GET", f"{base}/")
    assert home_status == "200", base
    _, agents_status = curl_request("GET", f"{base}/registry/rest/v1/registry-center/agent-cards")
    assert agents_status == "200", base
    uninstall = run(["sudo", "scripts/uninstall.sh", "--config", cfg.offline_config_env], cwd=bundle, timeout=1800)
    assert uninstall.exit_code == 0, uninstall.output
    releases = run(["helm", "ls", "-n", "openan"])
    assert "openan" not in releases.stdout, releases.output
