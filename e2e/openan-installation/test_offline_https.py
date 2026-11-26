import json

import pytest

from utils.env import install_config
from utils.offline_install import install_offline_k8s, offline_k8s_bundle, uninstall_offline_k8s
from utils.shell import kubectl, kubectl_jsonpath, run, save_evidence

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.offline,
    pytest.mark.P0,
    pytest.mark.smoke,
]

PROBE_POD = "openan-e2e-https-probe"

PYTHON_TLS_CHECK = (
    "import ssl, sys, urllib.request;"
    "ctx = ssl.create_default_context(cafile=sys.argv[1]);"
    "print(urllib.request.urlopen('https://registry-center:5000/health', context=ctx).status)"
)

TLS_SECRETS = {
    "openan-rc-tls": {"server.cer", "server_key.pem", "cert_pwd", "trust.cer"},
    "openan-oc-tls": {"server.cer", "server_key.pem", "cert_pwd", "trust.cer"},
    "openan-ingress-client": {"tls.crt", "tls.key", "ca.crt"},
}


def _json(args: list):
    result = kubectl(args)
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _secret_keys(name: str) -> set[str]:
    return set(_json(["-n", "openan", "get", "secret", name, "-o", "json"])["data"])


def _registry_ingress() -> dict:
    for item in _json(["-n", "openan", "get", "ingress", "-o", "json"])["items"]:
        backends = {
            path["backend"]["service"]["name"]
            for rule in item["spec"].get("rules", [])
            for path in rule["http"]["paths"]
        }
        if "registry-center" in backends:
            return item
    pytest.fail("no Ingress routes to the registry-center Service")


def _delete_probe(*, wait: bool) -> None:
    kubectl(["-n", "openan", "delete", "pod", PROBE_POD, "--ignore-not-found", f"--wait={'true' if wait else 'false'}"],
            timeout=120)


def _probe_https(image: str) -> tuple[int, str, str]:
    manifest = json.dumps({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": PROBE_POD, "namespace": "openan"},
        "spec": {
            "restartPolicy": "Never",
            "containers": [{
                "name": "probe",
                "image": image,
                "imagePullPolicy": "IfNotPresent",
                "command": ["python3", "-c", PYTHON_TLS_CHECK, "/ingress-client/ca.crt"],
                "volumeMounts": [{"name": "ingress-client", "mountPath": "/ingress-client", "readOnly": True}],
            }],
            "volumes": [{"name": "ingress-client", "secret": {"secretName": "openan-ingress-client"}}],
        },
    })
    _delete_probe(wait=True)
    created = run(["kubectl", "apply", "-f", "-"], stdin=manifest, timeout=120)
    assert created.exit_code == 0, created.output
    waited = kubectl(
        ["-n", "openan", "wait", "--for=jsonpath={.status.phase}=Succeeded", f"pod/{PROBE_POD}", "--timeout=240s"],
        timeout=300,
    )
    logs = kubectl(["-n", "openan", "logs", PROBE_POD], timeout=120)
    details = kubectl(["-n", "openan", "describe", "pod", PROBE_POD], timeout=120)
    _delete_probe(wait=False)
    evidence = (
        f"wait exit={waited.exit_code}\n{waited.output}\n"
        f"--- probe logs ---\n{logs.output}\n--- describe ---\n{details.output}"
    )
    return waited.exit_code, logs.stdout, evidence


@getattr(pytest.mark, "DFX-openan-installation-security-002")
@getattr(pytest.mark, "26-winter")
def test_offline_default_https_generated_ca(require_profile, cleanup):
    require_profile("offline-node")
    cfg = install_config()
    bundle = offline_k8s_bundle(cfg)
    cleanup.add("delete https probe pod", kubectl, "-n", "openan", "delete", "pod", PROBE_POD,
                "--ignore-not-found", "--wait=false", timeout=120)
    cleanup.add("offline k8s uninstall", uninstall_offline_k8s, bundle, cfg)
    install = install_offline_k8s(bundle, cfg)
    assert install.exit_code == 0, install.output
    for secret, keys in TLS_SECRETS.items():
        assert _secret_keys(secret) == keys, f"TLS Secret {secret} does not carry exactly {sorted(keys)}"
    annotations = _registry_ingress()["metadata"].get("annotations", {})
    assert annotations.get("nginx.ingress.kubernetes.io/backend-protocol") == "HTTPS", annotations
    assert annotations.get("nginx.ingress.kubernetes.io/proxy-ssl-verify") == "on", annotations
    image = kubectl_jsonpath("deploy/registry-center", "{.spec.template.spec.containers[0].image}").stdout.strip()
    assert image, "registry-center Deployment has no image reference"
    exit_code, stdout, evidence = _probe_https(image)
    save_evidence("security-002-https-probe", evidence)
    assert exit_code == 0 and "200" in stdout.split(), (
        f"in-cluster HTTPS access to /health with the shared CA failed:\n{evidence[-1500:]}"
    )
    uninstall = uninstall_offline_k8s(bundle, cfg)
    assert uninstall.exit_code == 0, uninstall.output
