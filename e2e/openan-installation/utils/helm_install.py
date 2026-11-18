from __future__ import annotations

import re
from pathlib import Path

from utils.env import InstallConfig
from utils.shell import CommandResult, kubectl, kubectl_jsonpath, run, run_interactive


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
        answers.append((r"component|which services|select", components_answer))
    answers.extend(
        [
            (r"admin[\w ]{0,30}password", cfg.admin_password),
            (r"(postgres|database)[\w ]{0,30}password", cfg.db_password),
            (r"(image[\w ]{0,10}tag|\btag\b)", cfg.image_tag),
            (r"model", cfg.llm_model),
            (r"(api[ ]?url|base[ ]?url|endpoint|url)", cfg.llm_api_url),
            (r"(api[ ]?key|\bkey\b)", cfg.llm_api_key),
        ]
    )
    return answers


def install_online_helm(
    cfg: InstallConfig,
    components_answer: str | None = None,
    evidence_stem: str | None = None,
) -> CommandResult:
    return run_interactive(
        "./install.sh",
        cwd=online_install_dir(cfg),
        answers=wizard_answers(cfg, components_answer),
        timeout=3600,
        evidence_stem=evidence_stem,
    )


def uninstall_online_helm(cfg: InstallConfig) -> CommandResult:
    return run("./uninstall.sh", cwd=online_install_dir(cfg), timeout=1800)


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
    match = re.search(r"(?:platform|url)[^\n]{0,60}(https?://[^\s\"']+)", transcript or "", re.IGNORECASE)
    if match:
        return match.group(1).rstrip("/")
    ip = kubectl_jsonpath("ingress", "{.items[0].status.loadBalancer.ingress[0].ip}").stdout.strip()
    if ip:
        return f"https://{ip}"
    host = kubectl_jsonpath("ingress", "{.items[0].spec.rules[0].host}").stdout.strip()
    return f"https://{host}" if host else "https://127.0.0.1"
