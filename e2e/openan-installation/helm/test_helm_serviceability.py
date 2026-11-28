import pytest

from utils.env import install_config
from utils.helm_install import (
    FULL_STACK_PODS,
    ensure_metallb_pool,
    helm_releases,
    install_online_helm,
    install_values,
    namespace_resources,
    pv_names_for_namespace,
    pvc_view,
    require_helm_env,
    uninstall_online_helm,
    wait_pods_ready,
)
from utils.shell import kubectl

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    getattr(pytest.mark, "registry-center"),
    getattr(pytest.mark, "orchestration-center"),
    pytest.mark.P1,
    pytest.mark.full,
]

RUNTIME_PVCS = ("registry-center-runtime", "orchestration-center-runtime")
BOUND_KEPT = "Bound keep"


@getattr(pytest.mark, "DFX-openan-installation-serviceability-007")
@getattr(pytest.mark, "26-winter")
def test_online_helm_uninstall_preserves_runtime_pvcs_until_data_cleanup_is_confirmed(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    install = install_online_helm(cfg, evidence_stem="serviceability-007-install")
    assert install.exit_code == 0, install.output
    assert wait_pods_ready(FULL_STACK_PODS), kubectl(["-n", "openan", "get", "pods"]).output
    view = pvc_view()
    for name in RUNTIME_PVCS:
        assert view.get(name) == BOUND_KEPT, f"{name} is {view.get(name)!r}"
    pvs = pv_names_for_namespace()
    uninstall = uninstall_online_helm(cfg, keep_data=True, keep_namespace=True)
    assert uninstall.exit_code == 0, uninstall.output
    assert helm_releases() == [], "the Helm release was not removed"
    view = pvc_view()
    for name in RUNTIME_PVCS:
        assert view.get(name) == BOUND_KEPT, f"{name} after uninstall is {view.get(name)!r}"
    assert pv_names_for_namespace() == pvs, "runtime PVs changed although data cleanup was declined"
    ensure_metallb_pool(cfg)
    reinstall = install_values(cfg)
    assert reinstall.exit_code == 0, reinstall.output
    assert wait_pods_ready(FULL_STACK_PODS), kubectl(["-n", "openan", "get", "pods"]).output
    final = uninstall_online_helm(cfg)
    assert final.exit_code == 0, final.output
    assert pvc_view() == {} and pv_names_for_namespace() == set(), "PVCs or PVs survived the full uninstall"
    assert namespace_resources() == [], namespace_resources()
