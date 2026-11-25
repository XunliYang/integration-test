from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from pathlib import Path

from utils.env import InstallConfig
from utils.shell import CommandResult, curl_request, kubectl, kubectl_jsonpath, run, run_interactive, wait_until

log = logging.getLogger("openan-e2e.helm")


def online_install_dir(cfg: InstallConfig) -> Path:
    return cfg.repo_path / "containerized" / "online-install"


def require_helm_env(cfg: InstallConfig) -> None:
    import pytest

    if not cfg.image_tag:
        pytest.skip("OPENAN_INSTALL_IMAGE_TAG is not set")
    if not (cfg.admin_password and cfg.db_password):
        pytest.skip("OPENAN_INSTALL_ADMIN_PASSWORD / OPENAN_INSTALL_DB_PASSWORD are not set")
    if not (cfg.llm_model and cfg.llm_api_url and cfg.llm_api_key):
        pytest.skip("OPENAN_INSTALL_LLM_MODEL / _API_URL / _API_KEY are not set")


def wizard_answers(cfg: InstallConfig, components_answer: str | None = None) -> list:
    answers = []
    if components_answer is not None:
        answers.append((r"components\s*\[", components_answer))
    answers.extend(
        [
            # install.sh: regenerate a leftover deployment.generated.json from a prior run
            (r"regenerate", "y"),
            # install.sh [2/4] infrastructure phase. Recreate the openan-pool
            # MetalLB range (uninstall.sh deletes it): leaving it empty strands
            # LoadBalancer services in <pending> on the next install.
            (r"install metallb", "y"),
            (r"metallb ip pool", "192.168.200.136-192.168.200.153"),
            # configure.py Step 1: components (full-stack default). The trailing "["
            # disambiguates the prompt from the "Components:" line in the deploy summary.
            (r"components\s*\[", "all"),
            # configure.py Step 2: image tags (narrow per-component matchers, in order)
            (r"registry-center image tag", cfg.image_tag),
            (r"orchestration-center image tag", cfg.image_tag),
            (r"frontend image", cfg.frontend_type),
            (r"portal image tag", cfg.portal_tag),
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
            # configure.py Step 5: signing & secrets
            (r"registry signing material", "auto"),
            (r"admin[\w ]{0,30}password", cfg.admin_password),
            (r"(postgres|database)[\w ]{0,30}password", cfg.db_password),
            # HTTPS self-signed (default yes): gen_certs.py lives at
            # <repo-root>/tool/gen_certs.py and configure.py resolves it via
            # parents[2], so the default path works on a full repo checkout.
            (r"enable https|self-signed", "yes"),
            # install.sh [4/4] deploy confirmation and optional demo agents server.
            (r"deploy with this", "y"),
            (r"agent examples server", "n"),
        ]
    )
    return answers


def install_online_helm(
    cfg: InstallConfig,
    components_answer: str | None = None,
    evidence_stem: str | None = None,
) -> CommandResult:
    # configure.py opens deployment.generated.json with O_EXCL; a leftover file
    # from a prior interrupted run makes it fail with EEXIST. Remove it first.
    generated = online_install_dir(cfg) / "deployment.generated.json"
    if generated.exists():
        generated.unlink()
    log.info("install_online_helm: components=%s evidence=%s", components_answer or "all", evidence_stem)
    t0 = time.time()
    result = run_interactive(
        str(online_install_dir(cfg) / "install.sh"),
        cwd=online_install_dir(cfg),
        answers=wizard_answers(cfg, components_answer),
        timeout=3600,
        evidence_stem=evidence_stem,
    )
    log.info("install_online_helm exit=%d elapsed=%.1fs output_tail=%s",
             result.exit_code, time.time() - t0, result.output[-200:])
    return result


def uninstall_online_helm(cfg: InstallConfig) -> CommandResult:
    log.info("uninstall_online_helm")
    t0 = time.time()
    result = run("./uninstall.sh", cwd=online_install_dir(cfg), timeout=1800)
    log.info("uninstall_online_helm exit=%d elapsed=%.1fs", result.exit_code, time.time() - t0)
    return result


def online_install_dir_chart(cfg: InstallConfig) -> Path:
    return online_install_dir(cfg) / "openan-chart"


def set_registry_signing(cfg: InstallConfig, enabled: bool) -> CommandResult:
    """Toggle card signature validation on the live registry by setting the
    REGISTRY_SIGNATURE_VALIDATION_ENABLED env var on the Deployment (the
    app's apply_env_overrides maps REGISTRY_* env to config keys), then
    rolling-restart the pod so the new env is picked up.

    This survives pod recreation (unlike sed on the image-baked server.conf,
    which is reverted when the container restarts from the image layer).
    """
    value = "true" if enabled else "false"
    log.info("set_registry_signing: REGISTRY_SIGNATURE_VALIDATION_ENABLED=%s", value)
    result = kubectl(["-n", "openan", "set", "env", "deploy/registry-center",
                      f"REGISTRY_SIGNATURE_VALIDATION_ENABLED={value}"])
    if result.exit_code != 0:
        log.error("set_registry_signing: kubectl set env failed: %s", result.output)
        return result
    # Rolling restart so the new env reaches the running process; wait for the
    # health endpoint to confirm the registry is serving again.
    kubectl(["-n", "openan", "rollout", "restart", "deploy/registry-center"])
    kubectl(["-n", "openan", "rollout", "status", "deploy/registry-center", "--timeout=300s"])

    def _registry_serving():
        _, status = curl_request("GET", f"{platform_base('')}/registry/health")
        return status == "200"
    wait_until(_registry_serving, timeout=120)
    log.info("set_registry_signing: registry serving again")
    return result


def pods_output() -> str:
    return kubectl(["-n", "openan", "get", "pods", "--no-headers"]).stdout or ""


def pod_name(fragment: str) -> str | None:
    for line in pods_output().splitlines():
        if not line.strip():
            continue
        name = line.split()[0]
        if fragment in name:
            return name
    return None


def all_pods_running_and_ready() -> bool:
    lines = [line for line in pods_output().splitlines() if line.strip()]
    return bool(lines) and all(("Running" in line and "1/1" in line) for line in lines)


def platform_base(transcript: str) -> str:
    # "Install complete" block: the platform URL is the wizard's own summary.
    match = re.search(r"Platform:\s*(https?://[^\s\"']+)", transcript or "", re.IGNORECASE)
    if match:
        return match.group(1).rstrip("/")
    ip = kubectl_jsonpath("ingress", "{.items[0].status.loadBalancer.ingress[0].ip}").stdout.strip()
    if ip:
        return f"https://{ip}"
    host = kubectl_jsonpath("ingress", "{.items[0].spec.rules[0].host}").stdout.strip()
    return f"https://{host}" if host else "https://127.0.0.1"


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
    # new/rotated entry is picked up, then wait for it to come back Ready.
    kubectl(["-n", "openan", "delete", "pod", "-l", "app=registry-center", "--wait=false"])
    wait_until(all_pods_running_and_ready, timeout=600)
    log.info("add_vendor_credential: registry pod ready")
    return token
