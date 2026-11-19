import pytest

from utils.env import install_config
from utils.helm_install import (
    all_pods_running_and_ready,
    install_online_helm,
    platform_base,
    require_helm_env,
    uninstall_online_helm,
)
from utils.oc_auth import get_admin_token
from utils.shell import curl_request, kubectl, run, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    getattr(pytest.mark, "registry-center"),
    getattr(pytest.mark, "orchestration-center"),
    getattr(pytest.mark, "openan-frontend"),
    getattr(pytest.mark, "openan-postgres"),
    pytest.mark.P0,
    pytest.mark.smoke,
]


def test_helm_wizard_full_stack_platform_usable(require_profile):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    install = install_online_helm(cfg, evidence_stem="helm-online-001")
    assert install.exit_code == 0, install.output
    assert "install complete" in install.output.lower(), install.output
    assert wait_until(all_pods_running_and_ready, timeout=600), kubectl(["-n", "openan", "get", "pods"]).output
    ingress = kubectl(["-n", "openan", "get", "ingress", "--no-headers"])
    ingress_lines = [line for line in ingress.stdout.splitlines() if line.strip()]
    assert ingress.exit_code == 0, ingress.output
    assert len(ingress_lines) >= 3, ingress.output
    base = platform_base(install.output)
    _, home_status = curl_request("GET", f"{base}/")
    assert home_status == "200", base
    token_body, token_status, _ = get_admin_token(base, cfg.admin_password, evidence_stem="helm-online-001")
    assert token_status == "200", f"{token_status} {token_body}"
    assert "access_token" in token_body, token_body
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    releases = run(["helm", "ls", "-n", "openan"])
    assert "openan" not in releases.stdout, releases.output
    remaining = kubectl(["-n", "openan", "get", "all", "--no-headers"])
    assert not any(line.strip() for line in remaining.stdout.splitlines()), remaining.output


def test_helm_wizard_registry_only_deploys_registry_center(require_profile):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    install = install_online_helm(cfg, components_answer="registry-center", evidence_stem="helm-components-001")
    assert install.exit_code == 0, install.output
    assert "install complete" in install.output.lower(), install.output
    assert wait_until(all_pods_running_and_ready, timeout=600), kubectl(["-n", "openan", "get", "pods"]).output
    pods = kubectl(["-n", "openan", "get", "pods", "--no-headers"]).stdout
    assert "registry-center-" in pods, pods
    assert "orchestration-center-" not in pods, pods
    assert "openan-frontend-" not in pods, pods
    base = platform_base(install.output)
    _, health_status = curl_request("GET", f"{base}/registry/health")
    assert health_status == "200", base
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    releases = run(["helm", "ls", "-n", "openan"])
    assert "openan" not in releases.stdout, releases.output
