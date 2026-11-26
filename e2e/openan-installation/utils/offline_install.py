from __future__ import annotations

import re
from pathlib import Path

from utils.env import InstallConfig
from utils.shell import CommandResult, run


def offline_k8s_bundle(cfg: InstallConfig) -> Path:
    import pytest

    if not (cfg.offline_k8s_bundle and cfg.offline_config_env):
        pytest.skip(
            "OPENAN_INSTALL_OFFLINE_K8S_BUNDLE / OPENAN_INSTALL_OFFLINE_CONFIG_ENV are not set"
        )
    return Path(cfg.offline_k8s_bundle)


def check_offline_env(bundle: Path, cfg: InstallConfig) -> CommandResult:
    return run(["sudo", "scripts/check-env.sh", "--config", cfg.offline_config_env], cwd=bundle, timeout=600)


def install_offline_k8s(bundle: Path, cfg: InstallConfig) -> CommandResult:
    return run(
        ["sudo", "scripts/install.sh", "--config", cfg.offline_config_env, "--yes"],
        cwd=bundle,
        timeout=3600,
    )


def uninstall_offline_k8s(bundle: Path, cfg: InstallConfig) -> CommandResult:
    return run(
        ["sudo", "scripts/uninstall.sh", "--config", cfg.offline_config_env, "--yes"],
        cwd=bundle,
        timeout=1800,
    )


def access_base(output: str) -> str:
    match = re.search(r"Access URL(?: \(NodePort\))?:\s*(https?://[^\s\"']+)", output)
    assert match, f"installer printed no Access URL:\n{output[-2000:]}"
    return match.group(1).rstrip("/")
