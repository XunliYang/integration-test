import pytest

from utils.env import install_config
from utils.helm_install import (
    FULL_STACK_PODS,
    all_pods_running_and_ready,
    install_online_helm,
    platform_base,
    require_helm_env,
    uninstall_online_helm,
)
from utils.oc_auth import TOKEN_FIELDS, get_admin_token
from utils.shell import curl_request, kubectl, run, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    pytest.mark.P0,
    pytest.mark.smoke,
]


def _pods() -> str:
    return kubectl(["-n", "openan", "get", "pods"]).output


def _assert_namespace_empty() -> None:
    releases = run(["helm", "ls", "-n", "openan"])
    assert "openan" not in releases.stdout, releases.output
    remaining = kubectl(["-n", "openan", "get", "all", "--no-headers"])
    assert not any(line.strip() for line in remaining.stdout.splitlines()), remaining.output


@getattr(pytest.mark, "FIT-openan-installation-helm-online-001")
@getattr(pytest.mark, "26-winter")
@getattr(pytest.mark, "registry-center")
@getattr(pytest.mark, "orchestration-center")
def test_helm_wizard_full_stack_platform_usable(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    install = install_online_helm(cfg, evidence_stem="helm-online-001")
    assert install.exit_code == 0, install.output
    assert "install complete" in install.output.lower(), install.output
    assert wait_until(lambda: all_pods_running_and_ready(FULL_STACK_PODS), timeout=600), _pods()
    ingress = kubectl(["-n", "openan", "get", "ingress", "--no-headers"])
    ingress_lines = [line for line in ingress.stdout.splitlines() if line.strip()]
    assert ingress.exit_code == 0, ingress.output
    assert len(ingress_lines) >= 3, ingress.output
    base = platform_base(install.output)
    home_ok = wait_until(lambda: curl_request("GET", f"{base}/")[1] == "200", timeout=120)
    _, home_status = curl_request("GET", f"{base}/")
    assert home_ok, f"platform home never became 200 (last: {home_status})"
    token = get_admin_token(base, cfg.admin_password, evidence_stem="helm-online-001")
    assert token.changed, (
        "first boot did not force the password change (expected 403 Password change required): "
        f"{token.status} {token.body}"
    )
    assert token.status == "200", f"{token.status} {token.body}"
    assert TOKEN_FIELDS <= token.payload.keys(), token.body
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    _assert_namespace_empty()


@getattr(pytest.mark, "FIT-openan-installation-helm-components-001")
@getattr(pytest.mark, "26-winter")
@getattr(pytest.mark, "registry-center")
def test_helm_wizard_registry_only_deploys_registry_center(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    install = install_online_helm(cfg, components_answer="registry", evidence_stem="helm-components-001")
    assert install.exit_code == 0, install.output
    assert "install complete" in install.output.lower(), install.output
    assert wait_until(lambda: all_pods_running_and_ready(("registry-center",)), timeout=600), _pods()
    pods = kubectl(["-n", "openan", "get", "pods", "--no-headers"]).stdout
    assert "orchestration-center-" not in pods, pods
    assert "openan-frontend-" not in pods, pods
    base = platform_base(install.output)
    # Pod Ready ≠ ingress endpoint synced; poll until the registry health
    # endpoint answers 200 through the ingress.
    health_ok = wait_until(
        lambda: curl_request("GET", f"{base}/registry/health")[1] == "200", timeout=120)
    _, health_status = curl_request("GET", f"{base}/registry/health")
    assert health_ok, f"registry health never became 200 (last: {health_status})"
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    _assert_namespace_empty()
