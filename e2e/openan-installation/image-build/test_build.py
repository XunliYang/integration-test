import re
import shutil
from pathlib import Path

import pytest

from utils.build_tools import (
    MULTI_ARCH,
    binary_build_dir,
    build_images,
    build_offline,
    image_reference,
    inspect_image,
    offline_bundle_paths,
    pack_offline,
    packed_bundles,
    record_retention,
    require_build_host,
    require_build_registry,
    tar_members,
)
from utils.env import install_config

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.full,
]


def _remove(paths) -> None:
    for path in paths:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)


@getattr(pytest.mark, "FIT-openan-installation-local-build-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P1
def test_build_sh_tags_and_pushes_images_to_custom_local_registry(require_profile, require_opt_in, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    require_build_host(cfg)
    require_build_registry(cfg)
    reference = image_reference(cfg, "registry-center")
    cleanup.add("record retention list", record_retention, reference)
    result = build_images(cfg, "registry")
    assert result.exit_code == 0, result.output
    assert "Build completed!" in result.stdout, result.output[-2000:]
    assert f"- {reference}" in result.stdout, result.output[-2000:]
    inspect = inspect_image(reference)
    assert inspect.exit_code == 0, inspect.output
    for platform in cfg.build_platforms.split(","):
        assert platform.strip() in inspect.stdout, f"{platform} missing from the manifest:\n{inspect.stdout}"
    assert reference in record_retention(reference).read_text(encoding="utf-8")


@getattr(pytest.mark, "FIT-openan-installation-local-build-002")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
def test_build_offline_sh_builds_bundle_from_local_source_trees(require_profile, require_opt_in, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    require_build_host(cfg)
    if not (cfg.registry_src and cfg.orchestration_src):
        pytest.skip("OPENAN_INSTALL_REGISTRY_SRC / OPENAN_INSTALL_ORCHESTRATION_SRC are not set")
    for source in (cfg.registry_src, cfg.orchestration_src):
        if not (Path(source) / "Dockerfile").is_file():
            pytest.fail(f"{source} has no Dockerfile")
    bundle, tarball = offline_bundle_paths(cfg)
    cleanup.add("delete build artifacts", _remove, [bundle, tarball])
    result = build_offline(cfg)
    assert result.exit_code == 0, result.output
    assert bundle.is_dir() and tarball.is_file(), f"offline bundle not produced under {bundle.parent}"
    for entry in ("images", "chart", "scripts", "SHA256SUMS"):
        assert (bundle / entry).exists(), f"{entry} missing from the offline bundle"
    _remove([bundle, tarball])
    assert not bundle.exists() and not tarball.exists()


@getattr(pytest.mark, "FIT-openan-installation-binary-pack-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
def test_pack_sh_builds_a_dual_architecture_binary_offline_bundle(require_profile, require_opt_in, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    require_build_host(cfg)
    dist = binary_build_dir(cfg) / "dist"
    existed = dist.is_dir()
    before = set(packed_bundles(cfg)) if existed else set()
    cleanup.add("delete packed bundles", _remove_packed, dist, existed, before)
    result = pack_offline(cfg)
    assert result.exit_code == 0, result.output
    created = [path for path in packed_bundles(cfg) if path not in before]
    assert any("registry-center" in path.name for path in created), created
    orchestration = next((path for path in created if "orchestration-center" in path.name), None)
    assert orchestration is not None, created
    for path in created:
        members = tar_members(path)
        for arch in ("x86_64", "aarch64"):
            assert any(re.search(rf"vendor/wheels/[^/]*manylinux[^/]*_{arch}\.whl$", member) for member in members), (
                f"{path.name} has no {arch} manylinux wheel"
            )
    assert any(member.startswith("registry-center-") for member in tar_members(created[0])), created[0]
    orchestration_members = tar_members(orchestration)
    assert any("/vendor/npm-cache/" in member for member in orchestration_members), "orchestration bundle has no npm cache"
    registry = next(path for path in created if "registry-center" in path.name)
    assert not any("/vendor/npm-cache/" in member for member in tar_members(registry)), (
        "registry-center bundle unexpectedly carries an npm cache"
    )
    _remove_packed(dist, existed, before)
    assert not [path for path in packed_bundles(cfg) if path not in before]


def _remove_packed(dist: Path, existed: bool, before: set) -> None:
    if not existed:
        shutil.rmtree(dist, ignore_errors=True)
        return
    for path in dist.glob("*-linux.tar.gz"):
        if path not in before:
            path.unlink(missing_ok=True)
    shutil.rmtree(dist / "build", ignore_errors=True)


@getattr(pytest.mark, "DFX-openan-installation-compatibility-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
def test_build_sh_produces_multi_arch_manifests_for_amd64_and_arm64(require_profile, require_opt_in, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    require_build_host(cfg)
    require_build_registry(cfg)
    references = [image_reference(cfg, image) for image in ("registry-center", "orchestration-center", "workflow-designer")]
    cleanup.add("record retention list", record_retention, *references)
    result = build_images(cfg, "registry", "orchestration", platforms=MULTI_ARCH)
    assert result.exit_code == 0, result.output
    assert "Build completed!" in result.stdout, result.output[-2000:]
    for reference in references:
        assert f"- {reference}" in result.stdout, result.output[-2000:]
        inspect = inspect_image(reference)
        assert inspect.exit_code == 0, inspect.output
        assert "linux/amd64" in inspect.stdout and "linux/arm64" in inspect.stdout, inspect.stdout
    assert all(reference in record_retention(*references).read_text(encoding="utf-8") for reference in references)
