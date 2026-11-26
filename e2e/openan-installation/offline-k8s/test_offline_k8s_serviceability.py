import pytest

from utils.helm_install import helm_releases, pv_names_for_namespace, wait_pods_ready
from utils.offline_install import (
    helm_revision,
    hostpath_dirs,
    install_offline_k8s,
    offline_k8s_bundle,
    pvc_names,
    secret_data,
    uninstall_offline_k8s,
)
from utils.env import install_config
from utils.shell import kubectl, strip_ansi

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.P1,
    pytest.mark.full,
]

OFFLINE_PODS = ("registry-center", "orchestration-center", "openan-frontend")


def _wait_offline_pods() -> None:
    assert wait_pods_ready(OFFLINE_PODS), kubectl(["-n", "openan", "get", "pods"]).output


@getattr(pytest.mark, "DFX-openan-installation-serviceability-002")
@getattr(pytest.mark, "26-winter")
def test_offline_installer_rerun_upgrades_release_in_place(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = offline_k8s_bundle(cfg)
    cleanup.add("offline k8s uninstall", uninstall_offline_k8s, bundle, cfg)
    install = install_offline_k8s(bundle, cfg, evidence_stem="serviceability-002-first")
    assert install.exit_code == 0, install.output
    _wait_offline_pods()
    revision, pvcs, credentials = helm_revision(), pvc_names(), secret_data("openan-db-credentials")
    rerun = install_offline_k8s(bundle, cfg, evidence_stem="serviceability-002-rerun")
    assert rerun.exit_code == 0, rerun.output
    assert "upgrading in place" in rerun.output, rerun.output[-2000:]
    _wait_offline_pods()
    assert helm_revision() == revision + 1, "the re-run did not create a new Helm revision"
    assert pvc_names() == pvcs, "PVCs changed after the re-run"
    assert secret_data("openan-db-credentials") == credentials, "openan-db-credentials was rotated"
    uninstall = uninstall_offline_k8s(bundle, cfg)
    assert uninstall.exit_code == 0, uninstall.output


@getattr(pytest.mark, "DFX-openan-installation-serviceability-005")
@getattr(pytest.mark, "26-winter")
def test_containerized_uninstall_removes_release_registry_and_optional_data(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = offline_k8s_bundle(cfg)
    cleanup.add("offline k8s uninstall", uninstall_offline_k8s, bundle, cfg)
    install = install_offline_k8s(bundle, cfg, evidence_stem="serviceability-005-install")
    assert install.exit_code == 0, install.output
    _wait_offline_pods()
    dirs_before = hostpath_dirs()
    uninstall = uninstall_offline_k8s(bundle, cfg)
    assert uninstall.exit_code == 0, uninstall.output
    assert helm_releases() == [], "the Helm release survived the uninstall"
    assert kubectl(["get", "namespace", "openan"], timeout=60).exit_code != 0, "namespace openan survived the uninstall"
    assert pv_names_for_namespace() == set(), "PVs of the openan namespace survived the uninstall"
    assert hostpath_dirs() == dirs_before, "hostPath data directories changed"
    assert "hostPath data on storage nodes was NOT touched (manual)" in strip_ansi(uninstall.output), uninstall.output[-2000:]
