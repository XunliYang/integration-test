import os
import shutil

import pytest

from utils.env import install_config
from utils.helm_install import (
    helm_releases,
    namespace_resources,
    online_install_dir,
    uninstall_online_helm,
)
from utils.shell import EVIDENCE_DIR, run_interactive

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    pytest.mark.P1,
    pytest.mark.full,
]

UNREACHABLE_KUBECONFIG = """apiVersion: v1
kind: Config
clusters:
- name: unreachable
  cluster:
    server: https://127.0.0.1:1
contexts:
- name: unreachable
  context:
    cluster: unreachable
    user: unreachable
current-context: unreachable
users:
- name: unreachable
  user:
    token: unused
"""


@getattr(pytest.mark, "DFX-openan-installation-diagnosability-002")
@getattr(pytest.mark, "26-winter")
def test_online_installer_precheck_fails_clearly_when_cluster_unreachable(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    for tool in ("kubectl", "helm", "python3"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} is not installed on the ops machine")
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    kubeconfig = EVIDENCE_DIR / "unreachable.kubeconfig"
    kubeconfig.parent.mkdir(parents=True, exist_ok=True)
    kubeconfig.write_text(UNREACHABLE_KUBECONFIG, encoding="utf-8")
    cleanup.add("delete temporary kubeconfig", kubeconfig.unlink, missing_ok=True)
    releases_before, resources_before = helm_releases(), namespace_resources()
    install = run_interactive(
        str(online_install_dir(cfg) / "install.sh"),
        cwd=online_install_dir(cfg),
        env={**os.environ, "KUBECONFIG": str(kubeconfig)},
        evidence_stem="diagnosability-002",
    )
    assert install.exit_code == 2, install.output
    assert "[1/4] Preflight" in install.output, install.output[-2000:]
    assert "Kubernetes cluster unreachable: kubectl cluster-info failed" in install.output, install.output[-2000:]
    assert "[2/4] Infrastructure" not in install.output, install.output[-2000:]
    assert helm_releases() == releases_before, "a release appeared although the preflight failed"
    assert namespace_resources() == resources_before, "resources appeared although the preflight failed"
