import pytest

from utils.env import install_config
from utils.offline_install import (
    INGRESS_CLIENT_SECRET,
    PROBE_POD,
    https_probe,
    ingress_annotation,
    install_offline_k8s,
    offline_k8s_bundle,
    pod_image,
    secret_data,
    uninstall_offline_k8s,
    volume_secret,
)
from utils.shell import kubectl

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.P0,
    pytest.mark.smoke,
]

TLS_SECRETS = {
    "openan-rc-tls": {"server.cer", "server_key.pem", "cert_pwd", "trust.cer"},
    "openan-oc-tls": {"server.cer", "server_key.pem", "cert_pwd", "trust.cer"},
    INGRESS_CLIENT_SECRET: {"tls.crt", "tls.key", "ca.crt"},
}


@getattr(pytest.mark, "DFX-openan-installation-security-002")
@getattr(pytest.mark, "26-winter")
def test_offline_default_https_generated_ca(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = offline_k8s_bundle(cfg)
    cleanup.add("delete https probe pod", kubectl, "-n", "openan", "delete", "pod", PROBE_POD,
                "--ignore-not-found", "--wait=false", timeout=120)
    cleanup.add("offline k8s uninstall", uninstall_offline_k8s, bundle, cfg)
    install = install_offline_k8s(bundle, cfg, evidence_stem="security-002")
    assert install.exit_code == 0, install.output
    for secret, keys in TLS_SECRETS.items():
        assert set(secret_data(secret)) == keys, f"TLS Secret {secret} does not carry exactly {sorted(keys)}"
    assert volume_secret("registry-center", "tls-certs") == "openan-rc-tls"
    assert ingress_annotation("openan-registry-ingress", "nginx.ingress.kubernetes.io/backend-protocol") == "HTTPS"
    assert ingress_annotation("openan-registry-ingress", "nginx.ingress.kubernetes.io/proxy-ssl-verify") == "on"
    image = pod_image("registry-center")
    assert image, "registry-center Deployment has no image reference"
    https_probe(image, INGRESS_CLIENT_SECRET, evidence_stem="security-002-https-probe")
    uninstall = uninstall_offline_k8s(bundle, cfg)
    assert uninstall.exit_code == 0, uninstall.output
