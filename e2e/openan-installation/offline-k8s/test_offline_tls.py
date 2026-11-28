import pytest

from utils.offline_install import (
    check_offline_env,
    configmap_value,
    https_probe,
    ingress_annotation,
    install_offline_k8s,
    offline_k8s_bundle,
    pod_image,
    probe_scheme,
    secret_uid,
    uninstall_offline_k8s,
    volume_secret,
    write_offline_config,
)
from utils.env import install_config
from utils.shell import EVIDENCE_DIR, kubectl, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
]

CUSTOM_SECRETS = {
    "RC_TLS_SECRET": "e2e-rc-tls",
    "OC_TLS_SECRET": "e2e-oc-tls",
    "INGRESS_CLIENT_SECRET": "e2e-ingress-client",
}
CERT_FILES = {
    "e2e-rc-tls": ("server.cer", "server_key.pem", "trust.cer", "cert_pwd"),
    "e2e-oc-tls": ("server.cer", "server_key.pem", "trust.cer", "cert_pwd"),
}


def _create_secret(name: str, pairs: list[str]) -> None:
    kubectl(["-n", "openan", "delete", "secret", name, "--ignore-not-found", "--wait=false"], timeout=120)
    created = kubectl(["-n", "openan", "create", "secret", "generic", name,
                       *[argument for pair in pairs for argument in ("--from-file", pair)]], timeout=120)
    assert created.exit_code == 0, f"Secret {name} not created: {created.output}"


@getattr(pytest.mark, "DFX-openan-installation-security-003")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P1
@pytest.mark.full
def test_user_provided_certificate_secrets_are_honored(require_profile, require_repo, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = offline_k8s_bundle(cfg)
    require_repo()
    certs = EVIDENCE_DIR / "security-003-certs"
    cleanup.add("delete custom TLS Secrets", kubectl, "-n", "openan", "delete", "secret",
                *CUSTOM_SECRETS.values(), "--ignore-not-found", "--wait=false", timeout=120)
    cleanup.add("offline k8s uninstall", uninstall_offline_k8s, bundle, cfg)
    generator = cfg.repo_dir / "tool" / "gen_certs_offline.py"
    if not generator.is_file():
        pytest.fail(f"{generator} is missing from the openan-installation checkout")
    generated = run(["python3", str(generator), "--out", str(certs), "--namespace", "openan"], timeout=300)
    assert generated.exit_code == 0, generated.output
    namespace = run(["kubectl", "create", "namespace", "openan", "--dry-run=client", "-o", "json"], timeout=120)
    applied = run(["kubectl", "apply", "-f", "-"], stdin=namespace.stdout, timeout=120)
    assert applied.exit_code == 0, applied.output
    for name, keys in CERT_FILES.items():
        component = "registry-center" if name == "e2e-rc-tls" else "orchestration-center"
        _create_secret(name, [f"{key}={certs / component / key}" for key in keys])
    _create_secret(CUSTOM_SECRETS["INGRESS_CLIENT_SECRET"], [
        f"tls.crt={certs / 'ingress-client' / 'tls.crt'}",
        f"tls.key={certs / 'ingress-client' / 'tls.key'}",
        f"ca.crt={certs / 'ca' / 'ca.cer'}",
    ])
    uids_before = {name: secret_uid(name) for name in CUSTOM_SECRETS.values()}
    config = write_offline_config(bundle, cfg, EVIDENCE_DIR / "offline-config" / "security-003", **CUSTOM_SECRETS)
    install = install_offline_k8s(bundle, cfg, config=config, evidence_stem="security-003")
    assert install.exit_code == 0, install.output
    assert volume_secret("registry-center", "tls-certs") == "e2e-rc-tls"
    assert volume_secret("orchestration-center", "tls-certs") == "e2e-oc-tls"
    for ingress in ("openan-registry-ingress", "openan-orchestration-ingress"):
        expected = f"openan/{CUSTOM_SECRETS['INGRESS_CLIENT_SECRET']}"
        assert ingress_annotation(ingress, "nginx.ingress.kubernetes.io/proxy-ssl-secret") == expected, ingress
    assert kubectl(["-n", "openan", "get", "secret", "openan-rc-tls"], timeout=120).exit_code != 0, (
        "an auto-generated openan-rc-tls Secret was created although custom Secrets were configured"
    )
    assert {name: secret_uid(name) for name in CUSTOM_SECRETS.values()} == uids_before, (
        "the user-provided Secrets were overwritten"
    )
    https_probe(pod_image("registry-center"), CUSTOM_SECRETS["INGRESS_CLIENT_SECRET"], pod="openan-e2e-custom-tls-probe",
                evidence_stem="security-003-https-probe")
    uninstall = uninstall_offline_k8s(bundle, cfg, config=config)
    assert uninstall.exit_code == 0, uninstall.output
    assert (certs / "ca" / "ca.cer").is_file(), "custom certificate material was deleted"


@getattr(pytest.mark, "DFX-openan-installation-security-004")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
@pytest.mark.full
def test_disabling_https_flips_the_whole_chain_with_explicit_warning(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = offline_k8s_bundle(cfg)
    config = write_offline_config(bundle, cfg, EVIDENCE_DIR / "offline-config" / "security-004", HTTPS_ENABLED="false")
    cleanup.add("delete config copy", config.unlink, missing_ok=True)
    cleanup.add("offline k8s uninstall", uninstall_offline_k8s, bundle, cfg, config)
    check = check_offline_env(bundle, cfg, config=config)
    assert check.exit_code == 0, check.output
    assert "HTTPS_ENABLED is not true" in check.output and "in-cluster traffic stays plain HTTP" in check.output, check.output
    install = install_offline_k8s(bundle, cfg, config=config, evidence_stem="security-004")
    assert install.exit_code == 0, install.output
    assert configmap_value("registry-center-config", "REGISTRY_ENABLE_HTTPS") == "false"
    assert configmap_value("registry-center-config", "REGISTRY_VERIFY_CLIENT") == "false"
    assert configmap_value("orchestration-center-config", "ORCH_ENABLE_HTTPS") == "false"
    assert configmap_value("orchestration-center-config", "ORCH_VERIFY_CLIENT") == "false"
    assert probe_scheme("registry-center") == "HTTP"
    assert volume_secret("orchestration-center", "tls-certs") == "", "orchestration-center still mounts a tls-certs volume"
    assert volume_secret("registry-center", "tls-certs") == "", "registry-center still mounts a tls-certs volume"
    uninstall = uninstall_offline_k8s(bundle, cfg, config=config)
    assert uninstall.exit_code == 0, uninstall.output
