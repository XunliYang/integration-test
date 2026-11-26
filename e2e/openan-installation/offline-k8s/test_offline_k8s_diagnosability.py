import pytest

from utils.helm_install import helm_releases, namespace_resources
from utils.offline_install import check_offline_env, offline_k8s_bundle, write_offline_config
from utils.env import install_config
from utils.shell import EVIDENCE_DIR

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.P1,
    pytest.mark.full,
]


@getattr(pytest.mark, "DFX-openan-installation-diagnosability-001")
@getattr(pytest.mark, "26-winter")
def test_offline_check_env_reports_exact_fix_for_each_missing_prerequisite(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = offline_k8s_bundle(cfg)
    broken = write_offline_config(bundle, cfg, EVIDENCE_DIR / "offline-config" / "diagnosability-001",
                                  INSTALL_METALLB="true", METALLB_POOL="")
    cleanup.add("delete config copy", broken.unlink, missing_ok=True)
    before = helm_releases(), namespace_resources()
    first = check_offline_env(bundle, cfg, config=broken)
    assert first.exit_code != 0, first.output
    assert "[FAIL]" in first.output, first.output
    assert "INSTALL_METALLB=true but METALLB_POOL is empty" in first.output, first.output
    assert "provide a routable internal range" in first.output, first.output
    second = check_offline_env(bundle, cfg)
    assert second.exit_code == 0, second.output
    assert "[FAIL]" not in second.output, second.output
    assert (helm_releases(), namespace_resources()) == before, "check-env changed cluster resources"
