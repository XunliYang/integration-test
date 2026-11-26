import re

import pytest

from utils.env import install_config
from utils.helm_install import (
    FULL_STACK_PODS,
    NODEPORT_PATCH,
    default_storage_classes,
    first_node_name,
    ingress_controller_service,
    install_online_helm,
    ip_in_pool,
    namespace_pods_running,
    nodeport_base,
    patch_ingress_controller_service,
    platform_base,
    remove_infra_namespaces,
    require_helm_env,
    restore_ingress_controller_service,
    set_default_storage_class,
    uninstall_online_helm,
    wait_pods_ready,
)
from utils.shell import curl_request, kubectl, kubectl_jsonpath, wait_until

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    pytest.mark.P1,
    pytest.mark.full,
]

FALLBACK_PVS = (
    ("openan-postgres-pv", "/data/openan-postgres"),
    ("openan-rc-pv", "/data/openan-registry"),
    ("openan-oc-pv", "/data/openan-orchestration"),
)
NODE_PORTS = {30080, 30443}


def _require_dedicated_cluster(cfg, case: str) -> None:
    if not cfg.dedicated_cluster:
        pytest.skip(f"OPENAN_INSTALL_DEDICATED_CLUSTER is not set to 1 ({case} changes cluster-wide state)")


@getattr(pytest.mark, "DFX-openan-installation-reliability-002")
@getattr(pytest.mark, "26-winter")
def test_storage_auto_detection_falls_back_to_hostpath_pv(require_profile, require_opt_in, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    _require_dedicated_cluster(cfg, "reliability-002")
    defaults = default_storage_classes()
    if not defaults:
        pytest.skip("the cluster has no default StorageClass; the fallback is already the only path")
    restore = lambda: [set_default_storage_class(name, True) for name in defaults]
    cleanup.add("restore default StorageClass", restore)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    for name in defaults:
        assert set_default_storage_class(name, False).exit_code == 0, f"could not unset the default flag on {name}"
    assert default_storage_classes() == []
    install = install_online_helm(cfg, evidence_stem="reliability-002")
    assert install.exit_code == 0, install.output
    assert "No default StorageClass found; enabling the local hostPath fallback" in install.output, install.output[-2000:]
    provisioner = kubectl_jsonpath("storageclass/openan-local", "{.provisioner}").stdout.strip()
    assert provisioner == "kubernetes.io/no-provisioner", provisioner
    node = first_node_name()
    for pv, path in FALLBACK_PVS:
        got = kubectl_jsonpath(
            f"pv/{pv}",
            "{.spec.hostPath.path} {.spec.persistentVolumeReclaimPolicy} {.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]}",
        ).stdout.split()
        assert got == [path, "Retain", node], f"{pv}: {got}"
    phases = kubectl(["-n", "openan", "get", "pvc", "-o", 'jsonpath={range .items[*]}{.status.phase}{"\\n"}{end}']).stdout.split()
    assert phases and set(phases) == {"Bound"}, f"PVC phases: {phases}"
    assert wait_pods_ready(FULL_STACK_PODS), kubectl(["-n", "openan", "get", "pods"]).output
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
    restore()
    assert default_storage_classes() == defaults


@getattr(pytest.mark, "DFX-openan-installation-reliability-004")
@getattr(pytest.mark, "26-winter")
def test_bare_metal_cluster_without_lb_gets_metallb_auto_provisioned_entry(require_profile, require_opt_in, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    _require_dedicated_cluster(cfg, "reliability-004")
    if not cfg.metallb_pool:
        pytest.skip("OPENAN_INSTALL_METALLB_POOL is not set")
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    remove_infra_namespaces()
    install = install_online_helm(cfg, evidence_stem="reliability-004")
    assert install.exit_code == 0, install.output
    assert f"Configuring MetalLB pool: {cfg.metallb_pool}" in install.output, install.output[-2000:]
    pool = kubectl_jsonpath("ipaddresspool/openan-pool", "{.spec.addresses}", namespace="metallb-system").stdout
    assert cfg.metallb_pool in pool, pool
    assert kubectl(["-n", "metallb-system", "get", "l2advertisement", "openan-l2"], timeout=120).exit_code == 0
    assert wait_until(lambda: namespace_pods_running("metallb-system"), timeout=300), "MetalLB pods are not Running"
    service = ingress_controller_service()
    vip = (service["status"].get("loadBalancer", {}).get("ingress") or [{}])[0].get("ip", "")
    assert service["spec"]["type"] == "LoadBalancer", service["spec"]["type"]
    assert ip_in_pool(vip, cfg.metallb_pool), f"EXTERNAL-IP {vip!r} is outside the pool {cfg.metallb_pool}"
    base = platform_base(install.output)
    home_ok = wait_until(lambda: curl_request("GET", f"{base}/")[1] == "200", timeout=180)
    assert home_ok and vip in base, f"platform entry {base} (VIP {vip}) never returned 200"
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output


@getattr(pytest.mark, "DFX-openan-installation-reliability-005")
@getattr(pytest.mark, "26-winter")
def test_cluster_without_metallb_gets_a_reachable_nodeport_entry_fallback(require_profile, require_opt_in, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg, require_pool=False)
    _require_dedicated_cluster(cfg, "reliability-005")
    cleanup.add("restore ingress-nginx Service", restore_ingress_controller_service)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    install = install_online_helm(cfg, metallb_pool="", evidence_stem="reliability-005")
    assert install.exit_code == 0, install.output
    for line in ("No MetalLB pool configured; LoadBalancer IPs stay pending on bare metal",
                 "No LoadBalancer IP; the NodePort serves the frontend only"):
        assert line in install.output, f"{line!r} missing:\n{install.output[-2000:]}"
    node_ip = re.search(r"://([^:/]+)", nodeport_base(install.output)).group(1)
    service = ingress_controller_service()
    assert not service["status"].get("loadBalancer", {}).get("ingress"), "an EXTERNAL-IP was assigned without a pool"
    patched = patch_ingress_controller_service(NODEPORT_PATCH)
    assert patched.exit_code == 0, patched.output
    service = ingress_controller_service()
    assert service["spec"]["type"] == "NodePort", service["spec"]["type"]
    assert {port["nodePort"] for port in service["spec"]["ports"]} == NODE_PORTS, service["spec"]["ports"]
    entry_ok = wait_until(lambda: curl_request("GET", f"http://{node_ip}:30080/")[1] == "200", timeout=180)
    assert entry_ok, f"http://{node_ip}:30080/ never returned 200"
    assert curl_request("GET", f"https://{node_ip}:30443/")[1] == "200", f"https://{node_ip}:30443/ is not reachable"
    restored = restore_ingress_controller_service()
    assert restored is None or restored.exit_code == 0, restored.output if restored else ""
    uninstall = uninstall_online_helm(cfg)
    assert uninstall.exit_code == 0, uninstall.output
