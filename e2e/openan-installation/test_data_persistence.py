import json

import pytest

from utils.agentcard import agent_path, make_sample_agent_card
from utils.env import install_config
from utils.helm_install import (
    FULL_STACK_PODS,
    add_vendor_credential,
    all_pods_running_and_ready,
    install_online_helm,
    platform_base,
    pod_name,
    require_helm_env,
    uninstall_online_helm,
)
from utils.shell import curl_request, kubectl, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    getattr(pytest.mark, "registry-center"),
    pytest.mark.P0,
    pytest.mark.smoke,
]


def _pods() -> str:
    return kubectl(["-n", "openan", "get", "pods"]).output


@getattr(pytest.mark, "DFX-openan-installation-reliability-001")
@getattr(pytest.mark, "26-winter")
def test_bundled_db_data_survives_pod_restart(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    install = install_online_helm(cfg, evidence_stem="reliability-001-install")
    assert install.exit_code == 0, install.output
    assert wait_until(lambda: all_pods_running_and_ready(FULL_STACK_PODS), timeout=600), _pods()
    base = platform_base(install.output)
    # The persistence check uses an unsigned card; the chart default
    # registry.signatureValidationEnabled=false accepts it as deployed.
    card = make_sample_agent_card()
    # Card writes on the main port require a vendor_agent bearer credential;
    # client certs are unused in the default token identity mode.
    vendor_headers = ["Content-Type: application/json",
                      f"Authorization: Bearer {add_vendor_credential()}"]
    register_body, register_status = curl_request(
        "POST",
        f"{base}/registry/rest/v1/registry-center/agent-cards",
        data=json.dumps({"agentCards": [card]}),
        headers=vendor_headers,
    )
    assert register_status == "201", f"agent registration failed: {register_status} {register_body}"
    detail_body, detail_status = curl_request(
        "GET",
        f"{base}/registry/rest/v1/registry-center/{agent_path(card)}",
        headers=vendor_headers,
    )
    assert detail_status == "200" and card["name"] in detail_body, f"{detail_status} {detail_body}"
    registry_pod = pod_name("registry-center")
    db_pod = pod_name("postgres") or pod_name("mysql")
    assert registry_pod, "registry-center pod not found"
    assert db_pod, "database pod not found"
    database = db_pod.rsplit("-", 1)[0]
    delete = kubectl(["-n", "openan", "delete", "pod", registry_pod, db_pod, "--wait=false"])
    assert delete.exit_code == 0, delete.output
    assert wait_until(lambda: all_pods_running_and_ready(("registry-center", database)), timeout=600), _pods()
    detail_body_after, detail_status_after = curl_request(
        "GET",
        f"{base}/registry/rest/v1/registry-center/{agent_path(card)}",
        headers=vendor_headers,
    )
    assert detail_status_after == "200" and card["name"] in detail_body_after, (
        f"data lost after pod restart: {detail_status_after} {detail_body_after}"
    )
    curl_request("DELETE", f"{base}/registry/rest/v1/registry-center/{agent_path(card)}",
                 headers=vendor_headers)
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
