import pytest

from utils.helm_install import default_storage_classes, first_node_name, wait_pods_ready
from utils.offline_install import (
    install_offline_k8s,
    offline_k8s_bundle,
    pod_images,
    uninstall_offline_k8s,
)
from utils.env import install_config
from utils.shell import EVIDENCE_DIR, kubectl, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.P1,
    pytest.mark.full,
]

OFFLINE_PODS = ("registry-center", "orchestration-center", "openan-frontend")


def _wait_offline_pods() -> None:
    assert wait_pods_ready(OFFLINE_PODS), kubectl(["-n", "openan", "get", "pods"]).output


def _storage_overrides() -> list[str]:
    if default_storage_classes():
        return []
    node = first_node_name()
    return [
        "--set", "database.storage.createStorageClass=true",
        "--set", "database.storage.storageClassName=openan-local",
        "--set", "database.storage.createPV=true",
        "--set", "database.storage.useHostPath=true",
        "--set", f"database.storage.nodeName={node}",
        "--set", "orchestration.persistence.createPV=true",
        "--set", "orchestration.persistence.useHostPath=true",
        "--set", "orchestration.persistence.storageClassName=openan-oc-runtime",
        "--set", f"orchestration.persistence.nodeName={node}",
    ]


@getattr(pytest.mark, "FIT-openan-installation-offline-k8s-002")
@getattr(pytest.mark, "26-winter")
def test_values_registry_prefix_replacement_installs_from_specified_local_registry(require_profile, require_repo, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = offline_k8s_bundle(cfg)
    require_repo()
    if not cfg.local_registry:
        pytest.skip("OPENAN_INSTALL_LOCAL_REGISTRY is not set")
    if not (bundle / "chart").is_dir():
        pytest.fail(f"the bundle has no chart/ directory: {bundle}")
    cleanup.add("offline k8s uninstall", uninstall_offline_k8s, bundle, cfg)
    setup = install_offline_k8s(bundle, cfg, evidence_stem="offline-k8s-002-setup")
    assert setup.exit_code == 0, setup.output
    _wait_offline_pods()
    teardown = uninstall_offline_k8s(bundle, cfg, answers=("y", "n", "n"))
    assert teardown.exit_code == 0, teardown.output
    example = cfg.repo_dir / "containerized" / "offline-install" / "example.values.yaml"
    values = EVIDENCE_DIR / "offline-k8s-002.values.yaml"
    values.write_text(example.read_text(encoding="utf-8").replace("<REG_HOST>", cfg.local_registry), encoding="utf-8")
    kubectl(["delete", "storageclass", "openan-local", "--ignore-not-found", "--wait=false"], timeout=120)
    helm = run(["helm", "upgrade", "--install", "openan", "chart", "-n", "openan", "--create-namespace",
                "-f", str(values), "--wait", "--timeout", "10m", *_storage_overrides()],
               cwd=bundle, timeout=900)
    assert helm.exit_code == 0, helm.output
    _wait_offline_pods()
    images = pod_images()
    prefix = f"{cfg.local_registry.rstrip('/')}/"
    assert images and all(image.startswith(prefix) for image in images), images
    removed = run(["helm", "uninstall", "openan", "-n", "openan"], cwd=bundle, timeout=600)
    assert removed.exit_code == 0, removed.output
    final = uninstall_offline_k8s(bundle, cfg)
    assert final.exit_code == 0, final.output
