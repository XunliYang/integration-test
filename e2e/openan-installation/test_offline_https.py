from pathlib import Path

import pytest

from utils.env import install_config
from utils.shell import kubectl, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    getattr(pytest.mark, "registry-center"),
    getattr(pytest.mark, "orchestration-center"),
    pytest.mark.P0,
    pytest.mark.smoke,
]

PYTHON_TLS_CHECK = (
    "import ssl, sys, urllib.request;"
    "ctx = ssl.create_default_context(cafile=sys.argv[1]);"
    "print(urllib.request.urlopen('https://registry-center:5000/health', context=ctx).status)"
)


def test_offline_default_https_generated_ca(require_profile):
    require_profile("offline-node")
    cfg = install_config()
    if not cfg.offline_k8s_bundle:
        pytest.skip("OPENAN_INSTALL_OFFLINE_K8S_BUNDLE is not set")
    bundle = Path(cfg.offline_k8s_bundle)
    install = run(["sudo", "scripts/install.sh", "--config", cfg.offline_config_env], cwd=bundle, timeout=3600)
    assert install.exit_code == 0, install.output
    secrets = kubectl(["-n", "openan", "get", "secret", "--no-headers"])
    assert secrets.exit_code == 0, secrets.output
    for secret in ("openan-rc-tls", "openan-oc-tls", "openan-ingress-client"):
        assert secret in secrets.stdout, f"TLS secret {secret} not generated"
    trust = kubectl(
        ["-n", "openan", "exec", "deploy/registry-center", "--", "sh", "-c", "find / -name trust.cer 2>/dev/null | head -1"],
        timeout=120,
    )
    trust_path = trust.stdout.strip()
    assert trust_path, f"trust.cer not found in registry-center pod: {trust.output}"
    verify = kubectl(
        ["-n", "openan", "exec", "deploy/registry-center", "--", "python3", "-c", PYTHON_TLS_CHECK, trust_path],
        timeout=120,
    )
    assert verify.exit_code == 0 and "200" in verify.stdout, verify.output
    uninstall = run(["sudo", "scripts/uninstall.sh", "--config", cfg.offline_config_env], cwd=bundle, timeout=1800)
    assert uninstall.exit_code == 0, uninstall.output
