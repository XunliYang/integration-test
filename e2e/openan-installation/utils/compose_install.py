from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from pathlib import Path

from utils.shell import CommandResult, EVIDENCE_DIR, register_secret, run, save_evidence

log = logging.getLogger("openan-e2e.compose")

CORE_SERVICES = {"registry-center", "orchestration-center", "openan-nginx"}
DATABASE_SERVICES = {"openan-mysql", "openan-postgres"}
GENERATED_FILES = ("registry.env", "orchestration.env", "registry-models.yaml",
                   "orchestration-models.yaml", "integration_credentials.conf")
SENTINEL = "/tmp/openan-inject-check"
MODELS = """models:
  chat:
    provider: openai_compatible
    model: e2e-placeholder
    url: http://127.0.0.1:9/v1/chat/completions
    api_key_env: LLM_CHAT_API_KEY
"""


class ComposeConfig:
    def __init__(self, directory: Path, database: str) -> None:
        self.directory = directory
        self.database = database
        self.project = "openan"

    @property
    def path(self) -> Path:
        return self.directory / "config.env"

    @property
    def volume(self) -> str:
        flavor = "postgres" if self.database == "postgresql" else "mysql"
        return f"{self.project}_{flavor}-data"


def _write(path: Path, lines: list) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)


def prepare_compose_config(database: str = "mysql", stem: str = "compose",
                           registry_db_password: str | None = None,
                           generated_dir: Path | None = None) -> ComposeConfig:
    directory = EVIDENCE_DIR / "compose-config" / f"{time.strftime('%Y%m%d-%H%M%S')}-{stem}"
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    db_password = secrets.token_hex(16)
    register_secret(db_password)
    if generated_dir is None:
        source = directory
        hmac_key, fingerprint = secrets.token_hex(32), secrets.token_hex(32)
        token = secrets.token_urlsafe(48)
        admin_password = "A1a!" + secrets.token_hex(8)
        register_secret(token, admin_password)
        _write(directory / "registry.env", [
            f"INTEGRATION_FINGERPRINT_KEY={fingerprint}",
            f"INTEGRATION_TOKEN_HMAC_KEY={hmac_key}",
            f"LLM_CHAT_API_KEY={secrets.token_hex(16)}",
        ])
        _write(directory / "orchestration.env", [
            f"OC_ADMIN_INITIAL_PASSWORD={admin_password}",
            f"REGISTRY_ACCESS_TOKEN={token}",
            f"LLM_CHAT_API_KEY={secrets.token_hex(16)}",
            "RETRIEVAL_VECTOR_ENABLED=false",
        ])
        digest = hmac.new(hmac_key.encode(), token.encode(), hashlib.sha256).hexdigest()
        _write(directory / "integration_credentials.conf", [
            "credential.orchestration.identity=orchestration-service",
            "credential.orchestration.role=partner_service",
            "credential.orchestration.enabled=true",
            f"credential.orchestration.token_hash={digest}",
        ])
        for service in ("registry", "orchestration"):
            _write(directory / f"{service}-models.yaml", MODELS.rstrip("\n").split("\n"))
    else:
        source = generated_dir
    config = ComposeConfig(directory, database)
    root_password = "POSTGRES_PASSWORD" if database == "postgresql" else "MYSQL_ROOT_PASSWORD"
    _write(config.path, [
        f"PROJECT_NAME={config.project}",
        "PUBLIC_BIND=0.0.0.0",
        "PUBLIC_PORT=8080",
        "PUBLIC_ENABLE_HTTPS=false",
        "FRONTEND_TYPE=portal",
        f"DATABASE_TYPE={database}",
        "DATABASE_INTERNAL=true",
        f"DB_PORT={'5432' if database == 'postgresql' else '3306'}",
        "REGISTRY_DB_NAME=registry_center",
        "REGISTRY_DB_USERNAME=registry",
        f"REGISTRY_DB_PASSWORD={registry_db_password or db_password}",
        "ORCH_DB_NAME=orchestration_center",
        "ORCH_DB_USERNAME=orchestration",
        f"ORCH_DB_PASSWORD={db_password}",
        f"{root_password}={db_password}",
        "REGISTRY_ENABLE_HTTPS=false",
        "REGISTRY_VERIFY_CLIENT=false",
        "ORCH_ENABLE_HTTPS=false",
        "ORCH_VERIFY_CLIENT=false",
        "BACKEND_VERIFY_SERVER=true",
        "ORCH_CLIENT_VERIFY_SERVER=true",
        "REGISTRY_SIGN_ENABLED=false",
        "REGISTRY_AUTH_MODE=static_bearer",
        f"REGISTRY_CREDENTIAL_FILE={(source / 'integration_credentials.conf').as_posix()}",
        f"REGISTRY_MODELS_FILE={(source / 'registry-models.yaml').as_posix()}",
        f"ORCH_MODELS_FILE={(source / 'orchestration-models.yaml').as_posix()}",
        f"REGISTRY_RUNTIME_ENV_FILE={(source / 'registry.env').as_posix()}",
        f"ORCH_RUNTIME_ENV_FILE={(source / 'orchestration.env').as_posix()}",
    ])
    return config


def set_config_value(config: ComposeConfig, key: str, value: str | None) -> None:
    path = config.path
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith(f"{key}=")]
    _write(path, lines + ([f"{key}={value}"] if value is not None else []))


def set_runtime_value(config: ComposeConfig, service: str, key: str, value: str | None) -> None:
    path = config.directory / f"{service}.env"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith(f"{key}=")]
    _write(path, lines + ([f"{key}={value}"] if value is not None else []))


def check_compose_env(bundle: Path, config: ComposeConfig) -> CommandResult:
    return run(["sudo", "scripts/check-env.sh", "--config", str(config.path)], cwd=bundle, timeout=600)


def install_compose(bundle: Path, config: ComposeConfig, evidence_stem: str | None = None) -> CommandResult:
    result = run(["sudo", "scripts/install.sh", "--config", str(config.path)], cwd=bundle, timeout=3600)
    if evidence_stem:
        save_evidence(evidence_stem, result.output)
    return result


def uninstall_compose(bundle: Path) -> CommandResult:
    return run(["sudo", "scripts/uninstall.sh"], cwd=bundle, timeout=1200)


def compose_services(bundle: Path) -> dict:
    result = run(["sudo", "cat", "runtime/compose.json"], cwd=bundle, timeout=120)
    assert result.exit_code == 0, f"runtime/compose.json is not readable: {result.stderr.strip()}"
    return json.loads(result.stdout)


def compose_project(bundle: Path) -> str:
    return compose_services(bundle)["name"]


def container_names(bundle: Path) -> list[str]:
    result = run(["sudo", "docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={compose_project(bundle)}",
                 "--format", "{{.Names}}"], timeout=120)
    assert result.exit_code == 0, result.output
    return sorted(result.stdout.split())


def container_env(container: str, key: str) -> str:
    result = run(["sudo", "docker", "exec", container, "printenv", key], timeout=120)
    assert result.exit_code == 0, f"{key} is not set in {container}: {result.stderr.strip()}"
    return result.stdout.strip()


def container_port_bindings(container: str) -> dict:
    result = run(["sudo", "docker", "inspect", "--format", "{{json .HostConfig.PortBindings}}", container], timeout=120)
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout or "{}")


def volume_created_at(volume: str) -> str:
    result = run(["sudo", "docker", "volume", "inspect", volume, "--format", "{{.CreatedAt}}"], timeout=120)
    assert result.exit_code == 0, f"volume {volume} not found: {result.stderr.strip()}"
    return result.stdout.strip()


def runtime_file_mtime(bundle: Path, name: str) -> str:
    result = run(["sudo", "stat", "-c", "%Y", f"runtime/{name}"], cwd=bundle, timeout=120)
    assert result.exit_code == 0, result.output
    return result.stdout.strip()


def runtime_path_exists(bundle: Path, relative: str) -> bool:
    return run(["sudo", "test", "-e", relative], cwd=bundle, timeout=120).exit_code == 0


def json_items(text: str) -> list[dict]:
    text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = [json.loads(line) for line in text.splitlines() if line.strip()]
    return parsed if isinstance(parsed, list) else [parsed]


def service_status(bundle: Path) -> dict[str, tuple[str, str]]:
    ps = run(["sudo", "docker", "compose", "-f", "runtime/compose.json", "ps", "--format", "json"],
             cwd=bundle, timeout=300)
    assert ps.exit_code == 0, ps.output
    items = [{key.lower(): value for key, value in item.items()} for item in json_items(ps.stdout)]
    assert all("health" in item for item in items), (
        f"docker compose >= 2.20 is required (ps --format json has no health field): {items}"
    )
    return {str(item["service"]): (str(item.get("state")), str(item.get("health"))) for item in items}


def admin_password(bundle: Path) -> str:
    environment = compose_services(bundle)["services"]["orchestration-center"]["environment"]
    password = environment.get("OC_ADMIN_INITIAL_PASSWORD", "").replace("$$", "$")
    assert password, "OC_ADMIN_INITIAL_PASSWORD is missing from runtime/compose.json"
    register_secret(password)
    return password


def reset_compose_state(bundle: Path) -> CommandResult:
    down = run(["sudo", "docker", "compose", "-f", "runtime/compose.json", "down", "--volumes", "--remove-orphans"],
               cwd=bundle, timeout=300)
    for service in ("registry-center", "orchestration-center"):
        run(["sudo", "rm", "-rf", f"runtime/{service}/data"], cwd=bundle, timeout=120)
    return down
