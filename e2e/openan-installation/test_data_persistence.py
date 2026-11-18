import json

import pytest

from utils.agentcard import agent_path, make_sample_agent_card
from utils.env import install_config
from utils.helm_install import (
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
    getattr(pytest.mark, "openan-postgres"),
    pytest.mark.P0,
    pytest.mark.smoke,
]


def test_bundled_db_data_survives_pod_restart(require_profile):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    install = install_online_helm(cfg, evidence_stem="reliability-001-install")
    assert install.exit_code == 0, install.output
    assert wait_until(all_pods_running_and_ready, timeout=600), kubectl(["-n", "openan", "get", "pods"]).output
    base = platform_base(install.output)
    card = make_sample_agent_card()
    register_body, register_status = curl_request(
        "POST",
        f"{base}/registry/rest/v1/registry-center/agent-cards",
        data=json.dumps(card),
        headers=["Content-Type: application/json"],
        use_client_certs=True,
    )
    assert register_status == "201", f"agent registration failed: {register_status} {register_body}"
    detail_body, detail_status = curl_request(
        "GET",
        f"{base}/registry/rest/v1/registry-center/{agent_path(card)}",
        use_client_certs=True,
    )
    assert detail_status == "200" and card["name"] in detail_body, f"{detail_status} {detail_body}"
    registry_pod = pod_name("registry-center")
    db_pod = pod_name("postgres") or pod_name("mysql")
    assert registry_pod, "registry-center pod not found"
    assert db_pod, "database pod not found"
    delete = kubectl(["-n", "openan", "delete", "pod", registry_pod, db_pod, "--wait=false"])
    assert delete.exit_code == 0, delete.output
    assert wait_until(all_pods_running_and_ready, timeout=600), kubectl(["-n", "openan", "get", "pods"]).output
    detail_body_after, detail_status_after = curl_request(
        "GET",
        f"{base}/registry/rest/v1/registry-center/{agent_path(card)}",
        use_client_certs=True,
    )
    assert detail_status_after == "200" and card["name"] in detail_body_after, (
        f"data lost after pod restart: {detail_status_after} {detail_body_after}"
    )
    curl_request("DELETE", f"{base}/registry/rest/v1/registry-center/{agent_path(card)}", use_client_certs=True)
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
