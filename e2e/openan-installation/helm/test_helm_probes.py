import time

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

# registry-center and orchestration-center start in parallel with the bundled
# database and exit with a storage error until its Service resolves, which costs
# them a few CrashLoopBackOff restarts on every fresh install. The other pods
# must come up without a restart. Whatever the count, it has to stay flat for
# the whole observation window: a count that keeps growing is a crash loop.
DB_DEPENDENT_PODS = ("registry-center", "orchestration-center")
STARTUP_RESTART_TOLERANCE = 3
RESTART_SETTLE_SECONDS = 120


def _restart_counts() -> dict[str, int]:
    pods = kubectl_jsonpath("pods", "{range .items[*]}{.metadata.name}{' '}{.status.containerStatuses[0].restartCount}{'\\n'}{end}").stdout
    counts = {}
    for line in pods.splitlines():
        name, _, count = line.rpartition(" ")
        if name.strip():
            counts[name] = int(count or 0)
    return counts


def _assert_restarts_stable() -> dict[str, int]:
    # Observation has to span the whole window: the counts are equal to their
    # first snapshot right after it is taken, so "wait until equal" would pass
    # at once. Any change inside the window is a pod that is still restarting.
    first = _restart_counts()
    assert first, "no pods in the openan namespace"
    deadline = time.monotonic() + RESTART_SETTLE_SECONDS
    while time.monotonic() < deadline:
        current = _restart_counts()
        assert current == first, f"restart counts changed inside the {RESTART_SETTLE_SECONDS}s window: {current} (was {first})"
        time.sleep(10)
    for name, count in first.items():
        limit = STARTUP_RESTART_TOLERANCE if name.startswith(DB_DEPENDENT_PODS) else 0
        assert count <= limit, f"{name} restarted {count} times (limit {limit}): {kubectl(['-n', 'openan', 'get', 'pods']).output}"
    return first


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
    _assert_restarts_stable()
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
