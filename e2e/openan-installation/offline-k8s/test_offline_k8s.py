import pytest

from utils.env import install_config
from utils.offline_install import (
    access_base,
    check_offline_env,
    install_offline_k8s,
    offline_k8s_bundle,
    uninstall_offline_k8s,
)
from utils.shell import curl_request, kubectl, kubectl_jsonpath, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.P0,
    pytest.mark.smoke,
]


@getattr(pytest.mark, "FIT-openan-installation-offline-k8s-001")
@getattr(pytest.mark, "26-winter")
@getattr(pytest.mark, "registry-center")
@getattr(pytest.mark, "orchestration-center")
def test_offline_k8s_bundle_install_fully_offline(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = offline_k8s_bundle(cfg)
    cleanup.add("offline k8s uninstall", uninstall_offline_k8s, bundle, cfg)
    check = check_offline_env(bundle, cfg)
    assert check.exit_code == 0, check.output
    assert "FAIL" not in check.stdout, check.output
    install = install_offline_k8s(bundle, cfg)
    assert install.exit_code == 0, install.output
    pods = kubectl(["-n", "openan", "get", "pods", "--no-headers"])
    assert pods.exit_code == 0, pods.output
    assert all("Running" in line for line in pods.stdout.splitlines() if line.strip()), pods.output
    ingress_address = kubectl_jsonpath("ingress", "{.items[*].status.loadBalancer.ingress[0].ip}").stdout.strip()
    assert ingress_address, "ingress has no ADDRESS"
    base = access_base(install.output)
    _, home_status = curl_request("GET", f"{base}/")
    assert home_status == "200", base
    _, agents_status = curl_request("GET", f"{base}/registry/rest/v1/registry-center/agent-cards")
    assert agents_status == "200", base
    uninstall = uninstall_offline_k8s(bundle, cfg)
    assert uninstall.exit_code == 0, uninstall.output
    releases = run(["helm", "ls", "-n", "openan"])
    assert "openan" not in releases.stdout, releases.output
