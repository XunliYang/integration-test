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


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def _setting(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


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
    registry_url: str
    binary_offline_dir: str
    build_host: bool
    build_registry: str
    build_namespace: str
    build_tag: str
    build_platforms: str
    dedicated_cluster: bool
    external_db_type: str
    external_db_host: str
    external_db_port: str
    external_db_password: str
    local_registry: str
    reg_version: str
    registry_src: str
    orchestration_src: str
    fresh_vm: bool
    probe_host: str

    @property
    def repo_dir(self) -> Path:
        if self.repo_path is None:
            raise InstallConfigError("OPENAN_INSTALL_REPO_PATH is not set")
        return self.repo_path

    @property
    def binary_dir(self) -> Path:
        return self.repo_dir / self.binary_subdir


def install_config() -> InstallConfig:
    profile = _setting("OPENAN_INSTALL_MACHINE_PROFILE")
    if not profile:
        raise InstallConfigError(
            "OPENAN_INSTALL_MACHINE_PROFILE is not set (allowed: online-vm | cluster-ops | offline-node)"
        )
    if profile not in PROFILES:
        raise InstallConfigError(f"unknown OPENAN_INSTALL_MACHINE_PROFILE: {profile}")
    repo_path = _setting("OPENAN_INSTALL_REPO_PATH")
    image_tag = _setting("OPENAN_INSTALL_IMAGE_TAG")
    return InstallConfig(
        machine_profile=profile,
        repo_path=Path(repo_path) if repo_path else None,
        binary_subdir=_setting("OPENAN_INSTALL_BINARY_SUBDIR", "binary/one-click"),
        llm_model=_setting("OPENAN_INSTALL_LLM_MODEL"),
        llm_api_url=_setting("OPENAN_INSTALL_LLM_API_URL"),
        llm_api_key=_setting("OPENAN_INSTALL_LLM_API_KEY"),
        image_tag=image_tag,
        portal_tag=_setting("OPENAN_INSTALL_PORTAL_TAG", "v1.0.0"),
        frontend_type=_setting("OPENAN_INSTALL_FRONTEND_TYPE", "workflow-designer"),
        admin_password=_setting("OPENAN_INSTALL_ADMIN_PASSWORD"),
        db_password=_setting("OPENAN_INSTALL_DB_PASSWORD"),
        metallb_pool=_setting("OPENAN_INSTALL_METALLB_POOL"),
        offline_k8s_bundle=_setting("OPENAN_INSTALL_OFFLINE_K8S_BUNDLE"),
        offline_compose_bundle=_setting("OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE"),
        offline_config_env=_setting("OPENAN_INSTALL_OFFLINE_CONFIG_ENV"),
        registry_url=_setting("OPENAN_INSTALL_REGISTRY_URL"),
        binary_offline_dir=_setting("OPENAN_INSTALL_BINARY_OFFLINE_DIR"),
        build_host=_flag("OPENAN_INSTALL_BUILD_HOST"),
        build_registry=_setting("OPENAN_INSTALL_BUILD_REGISTRY"),
        build_namespace=_setting("OPENAN_INSTALL_BUILD_NAMESPACE", "project-openan"),
        build_tag=_setting("OPENAN_INSTALL_BUILD_TAG") or image_tag,
        build_platforms=_setting("OPENAN_INSTALL_BUILD_PLATFORMS", "linux/amd64"),
        dedicated_cluster=_flag("OPENAN_INSTALL_DEDICATED_CLUSTER"),
        external_db_type=_setting("OPENAN_INSTALL_EXTERNAL_DB_TYPE"),
        external_db_host=_setting("OPENAN_INSTALL_EXTERNAL_DB_HOST"),
        external_db_port=_setting("OPENAN_INSTALL_EXTERNAL_DB_PORT"),
        external_db_password=_setting("OPENAN_INSTALL_EXTERNAL_DB_PASSWORD"),
        local_registry=_setting("OPENAN_INSTALL_LOCAL_REGISTRY"),
        reg_version=_setting("OPENAN_INSTALL_REG_VERSION"),
        registry_src=_setting("OPENAN_INSTALL_REGISTRY_SRC"),
        orchestration_src=_setting("OPENAN_INSTALL_ORCHESTRATION_SRC"),
        fresh_vm=_flag("OPENAN_INSTALL_FRESH_VM"),
        probe_host=_setting("OPENAN_INSTALL_PROBE_HOST"),
    )
