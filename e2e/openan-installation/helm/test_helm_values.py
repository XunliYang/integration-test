import pytest

from utils.env import install_config
from utils.helm_install import (
    FULL_STACK_PODS,
    configure_online_helm,
    ensure_metallb_pool,
    helm_install_values,
    helm_releases,
    install_values,
    namespace_resources,
    platform_base,
    require_helm_env,
    uninstall_online_helm,
    values_path,
    wait_pods_ready,
)
from utils.shell import curl_request, kubectl, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    pytest.mark.full,
]


def _frontend_images() -> list[str]:
    result = kubectl(["-n", "openan", "get", "pods", "-l", "app=openan-frontend",
                      "-o", 'jsonpath={range .items[*]}{.spec.containers[0].image}{"\\n"}{end}'], timeout=120)
    assert result.exit_code == 0, result.output
    return [image for image in result.stdout.splitlines() if image.strip()]


@getattr(pytest.mark, "FIT-openan-installation-helm-values-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P1
def test_non_interactive_install_with_values_completes(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    configure = configure_online_helm(cfg, evidence_stem="helm-values-001-configure")
    assert configure.exit_code == 0, configure.output
    assert "Deployment cancelled. Values kept at:" in configure.output, configure.output[-1500:]
    assert values_path(cfg).is_file(), f"{values_path(cfg)} was not generated"
    assert helm_releases() == [], "a cancelled deploy must not create a Helm release"
    install = install_values(cfg, evidence_stem="helm-values-001-install")
    assert install.exit_code == 0, install.output
    assert wait_pods_ready(FULL_STACK_PODS), kubectl(["-n", "openan", "get", "pods"]).output
    assert [release["status"] for release in helm_releases()] == ["deployed"], helm_releases()
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    assert helm_releases() == [] and namespace_resources() == []


@getattr(pytest.mark, "FIT-openan-installation-frontend-select-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
def test_frontend_type_workflow_designer_deploys_legacy_frontend(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    if cfg.frontend_type != "workflow-designer":
        pytest.skip("OPENAN_INSTALL_FRONTEND_TYPE must be workflow-designer for this case")
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    configure = configure_online_helm(cfg, evidence_stem="frontend-select-001-configure")
    assert configure.exit_code == 0, configure.output
    ensure_metallb_pool(cfg)
    helm = helm_install_values(cfg)
    assert helm.exit_code == 0, helm.output
    assert wait_pods_ready(FULL_STACK_PODS), kubectl(["-n", "openan", "get", "pods"]).output
    images = _frontend_images()
    assert images and all("workflow-designer" in image and "openan-portal" not in image for image in images), images
    base = platform_base("")
    home_ok = wait_until(lambda: curl_request("GET", f"{base}/")[1] == "200", timeout=180)
    assert home_ok, f"frontend page {base}/ never returned 200"
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    assert helm_releases() == []
