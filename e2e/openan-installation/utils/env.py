from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROFILES = ("online-vm", "cluster-ops", "offline-node")


class InstallConfigError(RuntimeError):
    pass


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _parse_env_file(path: Path) -> dict:
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = _unquote(value.strip())
    return values


def load_env(env_file: Path | None = None) -> dict:
    if env_file is None:
        env_file = Path(__file__).resolve().parents[2] / ".env"
    values = _parse_env_file(Path(env_file))
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values


@dataclass(frozen=True)
class InstallConfig:
    machine_profile: str
    repo_path: Path | None
    binary_subdir: str
    llm_model: str
    llm_api_url: str
    llm_api_key: str
    image_tag: str
    portal_tag: str
    frontend_type: str
    admin_password: str
    db_password: str
    metallb_pool: str
    offline_k8s_bundle: str
    offline_compose_bundle: str
    offline_config_env: str

    @property
    def repo_dir(self) -> Path:
        if self.repo_path is None:
            raise InstallConfigError("OPENAN_INSTALL_REPO_PATH is not set")
        return self.repo_path

    @property
    def binary_dir(self) -> Path:
        return self.repo_dir / self.binary_subdir


def install_config() -> InstallConfig:
    profile = os.getenv("OPENAN_INSTALL_MACHINE_PROFILE", "").strip()
    if not profile:
        raise InstallConfigError(
            "OPENAN_INSTALL_MACHINE_PROFILE is not set (allowed: online-vm | cluster-ops | offline-node)"
        )
    if profile not in PROFILES:
        raise InstallConfigError(f"unknown OPENAN_INSTALL_MACHINE_PROFILE: {profile}")
    repo_path = os.getenv("OPENAN_INSTALL_REPO_PATH", "").strip()
    return InstallConfig(
        machine_profile=profile,
        repo_path=Path(repo_path) if repo_path else None,
        binary_subdir=os.getenv("OPENAN_INSTALL_BINARY_SUBDIR", "binary/one-click"),
        llm_model=os.getenv("OPENAN_INSTALL_LLM_MODEL", "").strip(),
        llm_api_url=os.getenv("OPENAN_INSTALL_LLM_API_URL", "").strip(),
        llm_api_key=os.getenv("OPENAN_INSTALL_LLM_API_KEY", "").strip(),
        image_tag=os.getenv("OPENAN_INSTALL_IMAGE_TAG", "").strip(),
        portal_tag=os.getenv("OPENAN_INSTALL_PORTAL_TAG", "v1.0.0").strip(),
        frontend_type=os.getenv("OPENAN_INSTALL_FRONTEND_TYPE", "workflow-designer").strip(),
        admin_password=os.getenv("OPENAN_INSTALL_ADMIN_PASSWORD", "").strip(),
        db_password=os.getenv("OPENAN_INSTALL_DB_PASSWORD", "").strip(),
        metallb_pool=os.getenv("OPENAN_INSTALL_METALLB_POOL", "").strip(),
        offline_k8s_bundle=os.getenv("OPENAN_INSTALL_OFFLINE_K8S_BUNDLE", "").strip(),
        offline_compose_bundle=os.getenv("OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE", "").strip(),
        offline_config_env=os.getenv("OPENAN_INSTALL_OFFLINE_CONFIG_ENV", "").strip(),
    )
