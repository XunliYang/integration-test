import json

import pytest

from utils.env import install_config
from utils.helm_install import (
    FULL_STACK_PODS,
    configure_online_helm,
    ensure_metallb_pool,
    helm_install_values,
    pods_output,
    require_helm_env,
    uninstall_online_helm,
    wait_pods_ready,
)
from utils.shell import kubectl, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    getattr(pytest.mark, "openan-frontend"),
    pytest.mark.P2,
    pytest.mark.slow,
]

STRESS = "for i in 1 2 3 4 5 6 7 8; do yes >/dev/null 2>&1 & done"
STOP_STRESS = "kill $(pidof yes) 2>/dev/null || true"
MIN_REPLICAS, MAX_REPLICAS = 2, 10


def _hpa() -> dict:
    result = kubectl(["-n", "openan", "get", "hpa", "openan-frontend", "-o", "json"], timeout=120)
    assert result.exit_code == 0, f"HPA openan-frontend not found: {result.stderr}"
    return json.loads(result.stdout)


def _frontend_pods() -> list[str]:
    result = kubectl(["-n", "openan", "get", "pods", "-l", "app=openan-frontend", "-o", "jsonpath={.items[*].metadata.name}"], timeout=120)
    assert result.exit_code == 0, result.output
    return [name for name in result.stdout.split() if name]


def _exec_all(command: str) -> None:
    for pod in _frontend_pods():
        kubectl(["-n", "openan", "exec", pod, "--", "sh", "-c", command], timeout=120)


def _frontend_restarts() -> list[int]:
    result = kubectl(["-n", "openan", "get", "pods", "-l", "app=openan-frontend",
                      "-o", 'jsonpath={range .items[*]}{.status.containerStatuses[*].restartCount}{"\\n"}{end}'], timeout=120)
    return [int(value) for value in result.stdout.split() if value.isdigit()]


@getattr(pytest.mark, "DFX-openan-installation-performance-001")
@getattr(pytest.mark, "26-winter")
def test_hpa_scales_openan_frontend_on_cpu_pressure_and_scales_back(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    if kubectl(["top", "pods", "-n", "openan"], timeout=120).exit_code != 0:
        pytest.skip("metrics-server is not available (kubectl top does not work)")
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    configure = configure_online_helm(cfg, evidence_stem="performance-001-configure")
    assert configure.exit_code == 0, configure.output
    ensure_metallb_pool(cfg)
    helm = helm_install_values(cfg)
    assert helm.exit_code == 0, helm.output
    assert wait_pods_ready(FULL_STACK_PODS), kubectl(["-n", "openan", "get", "pods"]).output
    cleanup.add("stop CPU stress", _exec_all, STOP_STRESS)
    spec = _hpa()["spec"]
    assert spec["minReplicas"] == MIN_REPLICAS and spec["maxReplicas"] == MAX_REPLICAS, spec
    utilization = {
        metric["resource"]["name"]: metric["resource"]["target"]["averageUtilization"]
        for metric in spec["metrics"] if metric["type"] == "Resource"
    }
    assert utilization.get("cpu") == 70 and utilization.get("memory") == 80, utilization
    assert _hpa()["status"].get("currentReplicas") == MIN_REPLICAS, _hpa()["status"]
    _exec_all(STRESS)
    scaled_up = wait_until(
        lambda: _hpa()["status"].get("desiredReplicas", 0) > MIN_REPLICAS
        and _hpa()["status"].get("currentReplicas", 0) == _hpa()["status"].get("desiredReplicas"),
        timeout=600, interval=60,
    )
    assert scaled_up, f"HPA did not scale out under CPU pressure: {_hpa()['status']}"
    assert wait_pods_ready(FULL_STACK_PODS), kubectl(["-n", "openan", "get", "pods"]).output
    assert _frontend_restarts() and max(_frontend_restarts()) == 0, f"frontend pods restarted: {pods_output()}"
    _exec_all(STOP_STRESS)
    scaled_down = wait_until(
        lambda: _hpa()["status"].get("currentReplicas", MAX_REPLICAS) == MIN_REPLICAS,
        timeout=900, interval=60,
    )
    assert scaled_down, f"HPA did not scale back after the pressure stopped: {_hpa()['status']}"
    assert wait_pods_ready(FULL_STACK_PODS), kubectl(["-n", "openan", "get", "pods"]).output
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
