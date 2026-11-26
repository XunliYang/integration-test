import pytest

from utils.env import install_config
from utils.helm_install import (
    FULL_STACK_PODS,
    all_pods_running_and_ready,
    install_online_helm,
    require_helm_env,
    uninstall_online_helm,
)
from utils.shell import kubectl, kubectl_jsonpath, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    pytest.mark.P0,
    pytest.mark.smoke,
]


def _probe_field(deploy: str, jsonpath: str) -> str:
    return kubectl_jsonpath(f"deploy/{deploy}", jsonpath).stdout.strip()


@getattr(pytest.mark, "DFX-openan-installation-testability-001")
@getattr(pytest.mark, "26-winter")
def test_chart_probes_rendered_and_pods_ready(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    install = install_online_helm(cfg, evidence_stem="testability-001")
    assert install.exit_code == 0, install.output
    assert _probe_field("registry-center", "{.spec.template.spec.containers[0].livenessProbe.httpGet.path}") == "/health"
    assert _probe_field("registry-center", "{.spec.template.spec.containers[0].readinessProbe.httpGet.path}") == "/health"
    assert _probe_field("registry-center", "{.spec.template.spec.containers[0].livenessProbe.httpGet.port}") == "http"
    assert _probe_field("registry-center", "{.spec.template.spec.containers[0].readinessProbe.httpGet.port}") == "http"
    # OC probes are tcpSocket by design: no unauthenticated HTTP endpoint, and
    # an exec healthcheck cold-starts a second Python process (chart values note).
    assert _probe_field("orchestration-center", "{.spec.template.spec.containers[0].livenessProbe.tcpSocket.port}") == "http"
    assert _probe_field("orchestration-center", "{.spec.template.spec.containers[0].readinessProbe.tcpSocket.port}") == "http"
    assert _probe_field("orchestration-center", "{.spec.template.spec.containers[0].startupProbe.tcpSocket.port}") == "http"
    assert _probe_field("orchestration-center", "{.spec.template.spec.containers[0].startupProbe.failureThreshold}") == "24"
    assert _probe_field("orchestration-center", "{.spec.template.spec.containers[0].startupProbe.periodSeconds}") == "10"
    assert wait_until(lambda: all_pods_running_and_ready(FULL_STACK_PODS), timeout=600)
    pods = kubectl_jsonpath("pods", "{.items[*].status.containerStatuses[*].restartCount}")
    restart_counts = [int(value) for value in pods.stdout.strip().strip("{}").split() if value]
    assert restart_counts, pods.stdout
    assert all(value == 0 for value in restart_counts), (
        f"pods restarted after the installation (expected RESTARTS 0): {kubectl(['-n', 'openan', 'get', 'pods']).output}"
    )
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
