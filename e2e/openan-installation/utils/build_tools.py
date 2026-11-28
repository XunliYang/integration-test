from __future__ import annotations

import logging
import time
from pathlib import Path

from utils.env import InstallConfig
from utils.shell import CommandResult, EVIDENCE_DIR, run

log = logging.getLogger("openan-e2e.build")

RETENTION_LOG = "image-retention.log"
MULTI_ARCH = "linux/amd64,linux/arm64"


def build_dir(cfg: InstallConfig) -> Path:
    return cfg.repo_dir / "containerized" / "build"


def binary_build_dir(cfg: InstallConfig) -> Path:
    return cfg.repo_dir / "binary" / "build"


def build_offline_dir(cfg: InstallConfig) -> Path:
    return cfg.repo_dir / "containerized" / "offline-install" / "build"


def require_build_host(cfg: InstallConfig) -> None:
    import pytest

    if not cfg.build_host:
        pytest.skip("OPENAN_INSTALL_BUILD_HOST is not set to 1")
    if not cfg.build_tag:
        pytest.skip("OPENAN_INSTALL_BUILD_TAG (or OPENAN_INSTALL_IMAGE_TAG) is not set")


def require_build_registry(cfg: InstallConfig) -> None:
    import pytest

    if not cfg.build_registry:
        pytest.skip("OPENAN_INSTALL_BUILD_REGISTRY is not set")


def build_images(cfg: InstallConfig, *components: str, platforms: str | None = None) -> CommandResult:
    directory = build_dir(cfg)
    command = [
        "bash", str(directory / "build.sh"), *components,
        "--image-registry", cfg.build_registry,
        "--namespace", cfg.build_namespace,
        "--tag", cfg.build_tag,
        "--platforms", platforms or cfg.build_platforms,
    ]
    log.info("build_images: %s", " ".join(command))
    started = time.time()
    result = run(command, cwd=directory, timeout=3600)
    log.info("build_images exit=%d elapsed=%.1fs", result.exit_code, time.time() - started)
    return result


def build_offline(cfg: InstallConfig) -> CommandResult:
    directory = build_offline_dir(cfg)
    command = [
        "bash", str(directory / "build-offline.sh"),
        "--tag", cfg.build_tag,
        "--app-source", "build",
        "--registry-src", cfg.registry_src,
        "--orchestration-src", cfg.orchestration_src,
        "--platforms", cfg.build_platforms,
    ]
    log.info("build_offline: %s", " ".join(command))
    started = time.time()
    result = run(command, cwd=directory, timeout=7200)
    log.info("build_offline exit=%d elapsed=%.1fs", result.exit_code, time.time() - started)
    return result


def offline_bundle_paths(cfg: InstallConfig) -> tuple[Path, Path]:
    dist = build_offline_dir(cfg) / "dist"
    return dist / f"openan-offline-{cfg.build_tag}", dist / f"openan-offline-{cfg.build_tag}.tar.gz"


def pack_offline(cfg: InstallConfig) -> CommandResult:
    directory = binary_build_dir(cfg)
    started = time.time()
    result = run(["bash", str(directory / "pack.sh")], cwd=directory, timeout=7200)
    log.info("pack_offline exit=%d elapsed=%.1fs", result.exit_code, time.time() - started)
    return result


def packed_bundles(cfg: InstallConfig) -> list[Path]:
    return sorted((binary_build_dir(cfg) / "dist").glob("*-linux.tar.gz"))


def tar_members(path: Path) -> list[str]:
    result = run(["tar", "-tzf", str(path)], timeout=600)
    assert result.exit_code == 0, f"cannot list {path}: {result.stderr}"
    return [member for member in result.stdout.splitlines() if member.strip()]


def image_reference(cfg: InstallConfig, image: str) -> str:
    return f"{cfg.build_registry}/{cfg.build_namespace}/{image}:{cfg.build_tag}"


def inspect_image(reference: str) -> CommandResult:
    return run(["docker", "buildx", "imagetools", "inspect", reference], timeout=120)


def record_retention(*references: str) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    target = EVIDENCE_DIR / RETENTION_LOG
    with target.open("a", encoding="utf-8") as stream:
        stream.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} " + " ".join(references) + "\n")
    return target
