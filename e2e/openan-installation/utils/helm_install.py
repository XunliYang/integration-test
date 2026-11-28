from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import re
import secrets
import time
from collections.abc import Sequence
from pathlib import Path

from utils.agentcard import delete_card, fetch_card, make_sample_agent_card, register_card
from utils.env import InstallConfig
from utils.shell import (
    CommandResult,
    curl_request,
    kubectl,
    kubectl_jsonpath,
    register_secret,
    run,
    run_interactive,
    save_evidence,
    wait_until,
)

log = logging.getLogger("openan-e2e.helm")

FULL_STACK_PODS = ("registry-center", "orchestration-center", "openan-frontend", "openan-postgres")
NAMESPACE = "openan"
DEFAULT_STORAGE_CLASS_ANNOTATION = "storageclass.kubernetes.io/is-default-class"
KEEP_ANNOTATION = "helm.sh/resource-policy"
# install.sh configures the MetalLB pool as soon as the CRDs exist, before the
# validation webhook pods are Ready; see _metallb_webhook_cold_start().
METALLB_COLD_START_RETRIES = 1
METALLB_WEBHOOK_READY_TIMEOUT = 300
METALLB_POOL_MANIFEST = """apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: openan-pool
  namespace: metallb-system
spec:
  addresses:
  - {pool}
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: openan-l2
  namespace: metallb-system
spec:
  ipAddressPools:
  - openan-pool
"""
INGRESS_SERVICE = ["-n", "ingress-nginx", "svc", "ingress-nginx-controller"]
NODEPORT_PATCH = json.dumps([
    {"op": "replace", "path": "/spec/type", "value": "NodePort"},
    {"op": "add", "path": "/spec/ports/0/nodePort", "value": 30080},
    {"op": "add", "path": "/spec/ports/1/nodePort", "value": 30443},
])
LOADBALANCER_PATCH = json.dumps([
    {"op": "replace", "path": "/spec/type", "value": "LoadBalancer"},
    {"op": "remove", "path": "/spec/ports/0/nodePort"},
    {"op": "remove", "path": "/spec/ports/1/nodePort"},
])
EMPTY_OUTPUT = ("No resources found", "NotFound")


def online_install_dir(cfg: InstallConfig) -> Path:
    return cfg.repo_dir / "containerized" / "online-install"


def metallb_pool_exists() -> bool:
    result = kubectl(
        ["get", "ipaddresspool", "openan-pool", "-n", "metallb-system", "--ignore-not-found", "-o", "name"],
        timeout=60,
    )
    return result.exit_code == 0 and bool(result.stdout.strip())


def require_helm_env(cfg: InstallConfig, require_pool: bool = True) -> None:
    import pytest

    if not cfg.image_tag:
        pytest.skip("OPENAN_INSTALL_IMAGE_TAG is not set")
    if not (cfg.admin_password and cfg.db_password):
        pytest.skip("OPENAN_INSTALL_ADMIN_PASSWORD / OPENAN_INSTALL_DB_PASSWORD are not set")
    if not (cfg.llm_model and cfg.llm_api_url and cfg.llm_api_key):
        pytest.skip("OPENAN_INSTALL_LLM_MODEL / _API_URL / _API_KEY are not set")
    if require_pool and not cfg.metallb_pool and not metallb_pool_exists():
        pytest.skip("OPENAN_INSTALL_METALLB_POOL is not set and the cluster has no openan-pool IPAddressPool")


def wizard_answers(
    cfg: InstallConfig,
    components_answer: str | None = None,
    database: str = "postgresql",
    external_db: dict | None = None,
    deploy: bool = True,
    metallb_pool: str | None = None,
) -> list:
    pool = cfg.metallb_pool if metallb_pool is None else metallb_pool
    db_password = cfg.db_password if external_db is None else cfg.external_db_password
    answers = []
    answers.extend(
        [
            # install.sh: regenerate a leftover deployment.generated.json from a prior run
            (r"regenerate", "y"),
            # install.sh [2/4] infrastructure phase. Recreate the openan-pool
            # MetalLB range (uninstall.sh deletes it): leaving it empty strands
            # LoadBalancer services in <pending> on the next install.
            (r"install metallb", "y"),
            (r"metallb ip pool", pool),
            # configure.py Step 1: components (full-stack default, or the
            # caller's selection). The trailing "[" disambiguates the prompt
            # from the "Components:" line in the deploy summary.
            (r"components\s*\[", components_answer or "all"),
            # configure.py Step 2: image tags (narrow per-component matchers, in order)
            (r"registry-center image tag", cfg.image_tag),
            (r"orchestration-center image tag", cfg.image_tag),
            (r"frontend image", cfg.frontend_type),
            (r"portal image tag", cfg.portal_tag),
            # configure.py Step 3: SQL. "external SQL" as displayed is rejected by
            # choose() (it lower-cases the input), so the prefix "external" is sent.
            (r"Database \[", "external" if external_db else "in-cluster"),
            (r"Database backend \[", database),
            (r"External SQL type", external_db["type"] if external_db else ""),
            (r"External SQL host", external_db["host"] if external_db else ""),
            (r"External SQL port", external_db["port"] if external_db else ""),
            # configure.py Step 4: LLM. The chat/embed/rerank prompts all contain
            # "model"/"url"/"key", so match each capability's frame specifically and
            # skip the optional embed/rerank/A2A-T blocks.
            (r"configure llm", "now"),
            (r"chat[\w ]{0,20}model", cfg.llm_model),
            (r"chat[\w ]{0,20}url", cfg.llm_api_url),
            (r"chat[\w ]{0,20}key", cfg.llm_api_key),
            (r"embed[\w ]{0,20}model", ""),
            (r"rerank[\w ]{0,20}model", ""),
            (r"use same llm", "yes"),
            (r"a2a-t sdk negotiation model", ""),
            # configure.py Step 5: signing & secrets. The database password is
            # asked before the admin password, and the admin prompt is shown
            # only when orchestration is selected.
            (r"registry signing material", "auto"),
            (r"(postgres|database|mysql|SQL)[\w ]{0,30}password", db_password),
            (r"admin[\w ]{0,30}password", cfg.admin_password),
            # HTTPS self-signed (default yes): gen_certs.py lives at
            # <repo-root>/tool/gen_certs.py and configure.py resolves it via
            # parents[2], so the default path works on a full repo checkout.
            (r"enable https|self-signed", "yes"),
            # install.sh [4/4] deploy confirmation and optional demo agents server.
            (r"deploy with this", "y" if deploy else "n"),
            (r"agent examples server", "n"),
        ]
    )
    return answers


def install_online_helm(
    cfg: InstallConfig,
    components_answer: str | None = None,
    evidence_stem: str | None = None,
    **wizard_options,
) -> CommandResult:
    # configure.py opens deployment.generated.json with O_EXCL; a leftover file
    # from a prior interrupted run makes it fail with EEXIST. Remove it first.
    generated = values_path(cfg)
    if generated.exists():
        generated.unlink()
    log.info("install_online_helm: components=%s evidence=%s options=%s",
             components_answer or "all", evidence_stem, sorted(wizard_options))
    t0 = time.time()
    stem = evidence_stem
    attempt = 0
    while True:
        generated = values_path(cfg)
        if generated.exists():
            generated.unlink()
        if attempt:
            # A retry is only reachable after a failure in install.sh's
            # infrastructure phase, i.e. before any Helm release exists. Nothing
            # else has to be undone; the evidence stem is suffixed so the failed
            # attempt stays on disk.
            stem = f"{evidence_stem}-retry{attempt}" if evidence_stem else None
        result = run_interactive(
            str(online_install_dir(cfg) / "install.sh"),
            cwd=online_install_dir(cfg),
            answers=wizard_answers(cfg, components_answer, **wizard_options),
            timeout=3600,
            evidence_stem=stem,
        )
        log.info("install_online_helm exit=%d elapsed=%.1fs output_tail=%s",
                 result.exit_code, time.time() - t0, result.output[-200:])
        if result.exit_code == 0 or not _metallb_webhook_cold_start(result.output) or attempt >= METALLB_COLD_START_RETRIES:
            return result
        attempt += 1
        # The failed attempt exits a few seconds after the CRDs appear, long
        # before the webhook pods that serve them are Running. Let them come up
        # before the rerun, otherwise it fails the same way.
        wait_until(_metallb_webhook_ready, timeout=METALLB_WEBHOOK_READY_TIMEOUT)
        log.info("install_online_helm: MetalLB webhook was not ready, retrying (attempt %d)", attempt + 1)


def _metallb_webhook_cold_start(transcript: str) -> bool:
    """install.sh waits for the MetalLB CRDs but not for the webhook pods that
    serve them, so the first IPAddressPool apply right after a fresh MetalLB
    install can fail with an InternalError from the validation webhook. One rerun
    after _metallb_webhook_ready() gets past it."""
    return "metallb.io" in transcript and "failed calling webhook" in transcript


def _metallb_webhook_ready() -> bool:
    pods = kubectl(["-n", "metallb-system", "get", "deploy", "controller",
                    "-o", "jsonpath={.status.readyReplicas}/{.status.replicas}"], timeout=120).stdout.strip()
    return pods == "1/1"


def configure_online_helm(cfg: InstallConfig, evidence_stem: str | None = None, **wizard_options) -> CommandResult:
    return install_online_helm(cfg, evidence_stem=evidence_stem, deploy=False, **wizard_options)


def values_path(cfg: InstallConfig) -> Path:
    return online_install_dir(cfg) / "deployment.generated.json"


def install_values(cfg: InstallConfig, values: Path | None = None, evidence_stem: str | None = None) -> CommandResult:
    command = [
        "bash", str(online_install_dir(cfg) / "install.sh"),
        "--values", str(values or values_path(cfg)), "--skip-build", "--skip-infra",
    ]
    result = run(command, cwd=online_install_dir(cfg), timeout=1800)
    if evidence_stem:
        save_evidence(evidence_stem, result.output)
    log.info("install_values exit=%d", result.exit_code)
    return result


def helm_install_values(cfg: InstallConfig, values: Path | None = None, chart: str = "openan-chart",
                        set_args: Sequence[str] = ()) -> CommandResult:
    command = ["helm", "upgrade", "--install", "openan", chart, "-n", NAMESPACE,
               "--create-namespace", "-f", str(values or values_path(cfg))]
    for setting in set_args:
        command += ["--set", setting]
    command += ["--wait", "--timeout", "10m"]
    return run(command, cwd=online_install_dir(cfg), timeout=900)


def ensure_metallb_pool(cfg: InstallConfig) -> CommandResult | None:
    if not cfg.metallb_pool or metallb_pool_exists():
        return None
    return run(["kubectl", "apply", "-f", "-"],
               stdin=METALLB_POOL_MANIFEST.format(pool=cfg.metallb_pool), timeout=120)


def uninstall_online_helm(cfg: InstallConfig, keep_data: bool = False, keep_namespace: bool = False) -> CommandResult:
    log.info("uninstall_online_helm keep_data=%s keep_namespace=%s", keep_data, keep_namespace)
    t0 = time.time()
    # uninstall.sh asks three yes/no questions on stdin; answer them
    # explicitly so the run does not hang on an unattended stdin.
    answers = [
        (r"Remove persistent data[^\n]*\?", "n" if keep_data else "y"),   # default no
        (r"Delete namespace[^\n]*\?", "n" if keep_namespace else "y"),     # default yes
        (r"Proceed with uninstall\?", "y"),         # default yes
    ]
    result = run_interactive(
        f"bash {online_install_dir(cfg) / 'uninstall.sh'}",
        cwd=online_install_dir(cfg),
        answers=answers,
        timeout=1800,
    )
    log.info("uninstall_online_helm exit=%d elapsed=%.1fs", result.exit_code, time.time() - t0)
    return result


def pods_output() -> str:
    return kubectl(["-n", "openan", "get", "pods", "--no-headers"]).stdout or ""


def all_pods_running_and_ready(required: Sequence[str] = ()) -> bool:
    lines = [line.split() for line in pods_output().splitlines() if line.strip()]
    ready = {columns[0] for columns in lines if len(columns) >= 3 and columns[1] == "1/1" and columns[2] == "Running"}
    if not lines or len(ready) != len(lines):
        return False
    return all(any(name.startswith(prefix) for name in ready) for prefix in required)


def pod_name(fragment: str) -> str | None:
    for line in pods_output().splitlines():
        if not line.strip():
            continue
        name = line.split()[0]
        if fragment in name:
            return name
    return None


def wait_pods_ready(required: Sequence[str] = (), timeout: int = 600) -> bool:
    return bool(wait_until(lambda: all_pods_running_and_ready(required), timeout=timeout))


def helm_releases() -> list[dict]:
    return json.loads(run(["helm", "ls", "-n", NAMESPACE, "-o", "json"], timeout=120).stdout or "[]")


def namespace_resources() -> list[str]:
    result = kubectl(["-n", NAMESPACE, "get", "all", "--no-headers"], timeout=120)
    if result.exit_code != 0 and any(marker in result.stderr for marker in EMPTY_OUTPUT):
        return []
    assert result.exit_code == 0, result.output
    return [line for line in result.stdout.splitlines() if line.strip()]


def statefulsets() -> list[str]:
    result = kubectl(["-n", NAMESPACE, "get", "statefulset", "--no-headers"], timeout=120)
    if result.exit_code != 0 and any(marker in result.stderr for marker in EMPTY_OUTPUT):
        return []
    assert result.exit_code == 0, result.output
    return [line.split()[0] for line in result.stdout.splitlines() if line.strip()]


def pvc_view() -> dict[str, str]:
    result = kubectl(["-n", NAMESPACE, "get", "pvc", "-o", "json"], timeout=120)
    if result.exit_code != 0 and any(marker in result.stderr for marker in EMPTY_OUTPUT):
        return {}
    assert result.exit_code == 0, result.output
    view = {}
    for item in json.loads(result.stdout)["items"]:
        annotation = item["metadata"].get("annotations", {}).get(KEEP_ANNOTATION, "-")
        view[item["metadata"]["name"]] = f"{item['status'].get('phase')} {annotation}"
    return view


def pv_names_for_namespace() -> set[str]:
    result = kubectl(["get", "pv", "-o", "json"], timeout=120)
    assert result.exit_code == 0, result.output
    return {item["metadata"]["name"] for item in json.loads(result.stdout)["items"]
            if (item["spec"].get("claimRef") or {}).get("namespace") == NAMESPACE}


def namespace_pods_running(namespace: str) -> bool:
    result = kubectl(["-n", namespace, "get", "pods", "-o", "json"], timeout=120)
    items = json.loads(result.stdout)["items"] if result.exit_code == 0 else []
    return bool(items) and all(
        item["status"]["phase"] == "Running" and all(status["ready"] for status in item["status"].get("containerStatuses", []))
        for item in items
    )


def platform_base(transcript: str, timeout: int = 180) -> str:
    # "Install complete" block: the platform URL is the wizard's own summary.
    match = re.search(r"Platform:\s*(https?://[^\s\"']+)", transcript or "", re.IGNORECASE)
    if match:
        return match.group(1).rstrip("/")
    # No transcript (values-mode deploy): the Ingress status gets its address
    # some time after the Pods are Ready, so poll for it.
    ip = wait_until(
        lambda: kubectl_jsonpath("ingress", "{.items[0].status.loadBalancer.ingress[0].ip}").stdout.strip(),
        timeout=timeout,
    )
    if ip:
        return f"https://{ip}"
    host = kubectl_jsonpath("ingress", "{.items[0].spec.rules[0].host}").stdout.strip()
    return f"https://{host}" if host else "https://127.0.0.1"


def nodeport_base(transcript: str) -> str:
    match = re.search(r"Platform \(NodePort\):\s*(https?://[^\s\"']+)", transcript or "", re.IGNORECASE)
    assert match, f"installer printed no NodePort platform URL:\n{(transcript or '')[-1500:]}"
    return match.group(1).rstrip("/")


def first_node_name() -> str:
    return kubectl(["get", "nodes", "-o", "jsonpath={.items[0].metadata.name}"], timeout=120).stdout.strip()


def default_storage_classes() -> list[str]:
    result = kubectl(["get", "storageclass", "-o", "json"], timeout=120)
    if result.exit_code != 0:
        return []
    return sorted(
        item["metadata"]["name"] for item in json.loads(result.stdout)["items"]
        if item["metadata"].get("annotations", {}).get(DEFAULT_STORAGE_CLASS_ANNOTATION) == "true"
    )


def set_default_storage_class(name: str, enabled: bool) -> CommandResult:
    patch = json.dumps({"metadata": {"annotations": {
        DEFAULT_STORAGE_CLASS_ANNOTATION: "true" if enabled else "false"}}})
    return kubectl(["patch", "storageclass", name, "--type", "merge", "-p", patch], timeout=120)


def remove_infra_namespaces(timeout: int = 600) -> None:
    kubectl(["delete", "validatingwebhookconfiguration", "ingress-nginx-admission",
             "--ignore-not-found", "--wait=false"], timeout=120)
    for name in ("metallb-system", "ingress-nginx"):
        kubectl(["delete", "namespace", name, "--ignore-not-found", "--wait=false"], timeout=120)
        kubectl(["wait", "--for=delete", f"namespace/{name}", f"--timeout={timeout}s"], timeout=timeout + 60)


def ingress_controller_service() -> dict:
    result = kubectl(["-n", "ingress-nginx", "get", "svc", "ingress-nginx-controller", "-o", "json"], timeout=120)
    assert result.exit_code == 0, f"ingress-nginx-controller Service not found: {result.output}"
    return json.loads(result.stdout)


def patch_ingress_controller_service(patch: str) -> CommandResult:
    return kubectl(["-n", "ingress-nginx", "patch", "svc", "ingress-nginx-controller",
                    "--type", "json", "-p", patch], timeout=120)


def restore_ingress_controller_service() -> CommandResult | None:
    service = ingress_controller_service()
    if service["spec"]["type"] != "NodePort":
        return None
    patch = [{"op": "replace", "path": "/spec/type", "value": "LoadBalancer"}]
    for index, port in enumerate(service["spec"]["ports"]):
        if "nodePort" in port:
            patch.append({"op": "remove", "path": f"/spec/ports/{index}/nodePort"})
    return patch_ingress_controller_service(json.dumps(patch))


def ip_in_pool(ip: str, pool: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
        if "/" in pool:
            return address in ipaddress.ip_network(pool, strict=False)
        start, _, end = pool.partition("-")
        return ipaddress.ip_address(start) <= address <= ipaddress.ip_address(end)
    except ValueError:
        return False


def exercise_agent_data_path(platform: str) -> tuple[str, str, str, str]:
    card = make_sample_agent_card()
    headers = ["Authorization: Bearer " + add_vendor_credential()]
    register_body, register_status = register_card(f"{platform}/registry", card, headers)
    query_body, query_status = fetch_card(f"{platform}/registry", card, headers)
    delete_card(f"{platform}/registry", card, headers)
    return register_status, register_body, query_status, query_body


def add_vendor_credential(identity: str = "e2e-vendor") -> str:
    """Append a vendor_agent credential to the registry's
    integration_credentials.conf and return the plaintext bearer token.

    Card writes on the main port are restricted to vendor_agent credentials
    (agent_registry/main_auth.py); the wizard only provisions a partner_service
    token for orchestration, which is 403 there. Reuses an existing entry when
    the identity is already present (the parser rejects duplicate identities).
    The Secret is recreated by the wizard on each install (uninstall deletes
    it), so no cleanup needed.
    """
    hmac_key = kubectl_jsonpath(
        "secret/openan-rc-runtime", "{.data.INTEGRATION_TOKEN_HMAC_KEY}").stdout.strip()
    if not hmac_key:
        raise RuntimeError("openan-rc-runtime Secret has no INTEGRATION_TOKEN_HMAC_KEY")
    hmac_key = base64.b64decode(hmac_key).decode()
    conf_b64 = kubectl_jsonpath(
        "secret/openan-rc-credentials", "{.data.integration_credentials\\.conf}").stdout.strip()
    conf = base64.b64decode(conf_b64).decode() if conf_b64 else ""
    token = secrets.token_urlsafe(48)
    register_secret(token)
    digest = hmac.new(hmac_key.encode(), token.encode(), hashlib.sha256).hexdigest()
    if f"credential.{identity}.identity=" in conf:
        # Identity already present (e.g. from an earlier interrupted run); the
        # plaintext token is unrecoverable, so rotate the entry in place.
        lines = [l for l in conf.splitlines()
                 if not l.startswith(f"credential.{identity}.")]
        conf = "\n".join(l for l in lines if l.strip()) + "\n"
    conf += (f"credential.{identity}.identity={identity}\n"
             f"credential.{identity}.role=vendor_agent\n"
             f"credential.{identity}.enabled=true\n"
             f"credential.{identity}.token_hash={digest}\n")
    patch = json.dumps([{"op": "replace",
                         "path": "/data/integration_credentials.conf",
                         "value": base64.b64encode(conf.encode()).decode()}])
    result = kubectl(["-n", "openan", "patch", "secret", "openan-rc-credentials",
                      "--type=json", "-p", patch])
    if result.exit_code != 0:
        log.error("add_vendor_credential: patch failed: %s", result.output)
        raise RuntimeError(f"failed to patch openan-rc-credentials: {result.output}")
    log.info("add_vendor_credential: patched openan-rc-credentials, recycling registry pod")
    # The credentials file is read at startup; recycle the registry pod so the
    # new/rotated entry is picked up, then poll the health endpoint until the
    # registry actually serves through the ingress (pod Ready ≠ endpoint synced).
    kubectl(["-n", "openan", "delete", "pod", "-l", "app=registry-center", "--wait=false"])
    wait_until(lambda: all_pods_running_and_ready(("registry-center",)), timeout=600)
    log.info("add_vendor_credential: registry pod ready")

    def _registry_serving():
        _, status = curl_request("GET", f"{platform_base('')}/registry/health")
        return status == "200"
    wait_until(_registry_serving, timeout=180)
    log.info("add_vendor_credential: registry serving again")
    return token
