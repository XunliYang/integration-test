from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from utils.env import InstallConfig
from utils.shell import CommandResult, kubectl, kubectl_jsonpath, run, save_evidence

TLS_CHECK = (
    "import ssl, sys, urllib.request;"
    "ctx = ssl.create_default_context(cafile=sys.argv[1]);"
    "print(urllib.request.urlopen(sys.argv[2], context=ctx).status)"
)
# registry-center v1.0.0 has no /health route; the offline chart's own probes
# use the query endpoint, which answers 200 once the service is up.
REGISTRY_TLS_URL = "https://registry-center:5000/rest/v1/registry-center/agent-cards"
PROBE_POD = "openan-e2e-https-probe"
INGRESS_CLIENT_SECRET = "openan-ingress-client"


def offline_k8s_bundle(cfg: InstallConfig) -> Path:
    import pytest

    if not (cfg.offline_k8s_bundle and cfg.offline_config_env):
        pytest.skip(
            "OPENAN_INSTALL_OFFLINE_K8S_BUNDLE / OPENAN_INSTALL_OFFLINE_CONFIG_ENV are not set"
        )
    return Path(cfg.offline_k8s_bundle)


def offline_config_path(bundle: Path, cfg: InstallConfig) -> Path:
    path = Path(cfg.offline_config_env)
    return path if path.is_absolute() else bundle / path


def read_offline_config(bundle: Path, cfg: InstallConfig) -> str:
    path = offline_config_path(bundle, cfg)
    result = run(["cat", str(path)], timeout=60)
    if result.exit_code != 0:
        result = run(["sudo", "cat", str(path)], timeout=60)
    assert result.exit_code == 0, f"cannot read {path}: {result.stderr.strip()}"
    return result.stdout


def write_offline_config(bundle: Path, cfg: InstallConfig, directory: Path, **overrides) -> Path:
    pending = dict(overrides)
    lines = []
    for line in read_offline_config(bundle, cfg).splitlines():
        text = line.strip()
        key = text.split("=", 1)[0].strip() if text and not text.startswith("#") and "=" in text else None
        if key in pending:
            value = pending.pop(key)
            lines.append(line if value is None else f'{key}="{value}"')
        else:
            lines.append(line)
    lines += [f'{key}="{value}"' for key, value in pending.items() if value is not None]
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "config.env"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    target.chmod(0o600)
    return target


def _config_argument(bundle: Path, cfg: InstallConfig, config: Path | None) -> str:
    return str(config) if config else cfg.offline_config_env


def check_offline_env(bundle: Path, cfg: InstallConfig, config: Path | None = None) -> CommandResult:
    return run(["sudo", "scripts/check-env.sh", "--config", _config_argument(bundle, cfg, config)],
               cwd=bundle, timeout=600)


def install_offline_k8s(
    bundle: Path,
    cfg: InstallConfig,
    config: Path | None = None,
    evidence_stem: str | None = None,
) -> CommandResult:
    result = run(
        ["sudo", "scripts/install.sh", "--config", _config_argument(bundle, cfg, config), "--yes"],
        cwd=bundle,
        timeout=3600,
    )
    if evidence_stem:
        save_evidence(evidence_stem, result.output)
    return result


def uninstall_offline_k8s(
    bundle: Path,
    cfg: InstallConfig,
    config: Path | None = None,
    answers: Sequence[str] | None = None,
) -> CommandResult:
    # answers are consumed in prompt order: persistent data, MetalLB pool, namespace
    command = ["sudo", "scripts/uninstall.sh", "--config", _config_argument(bundle, cfg, config)]
    stdin = None
    if answers is None:
        command.append("--yes")
    else:
        stdin = "".join(f"{answer}\n" for answer in answers)
    return run(command, cwd=bundle, timeout=1800, stdin=stdin)


def access_base(output: str) -> str:
    match = re.search(r"Access URL(?: \(NodePort\))?:\s*(https?://[^\s\"']+)", output)
    assert match, f"installer printed no Access URL:\n{output[-2000:]}"
    return match.group(1).rstrip("/")


def helm_revision() -> int:
    result = run(["helm", "history", "openan", "-n", "openan", "-o", "json"], timeout=120)
    assert result.exit_code == 0, result.output
    return max(int(item["revision"]) for item in json.loads(result.stdout))


def pvc_names() -> list[str]:
    result = kubectl(["-n", "openan", "get", "pvc", "-o", 'jsonpath={range .items[*]}{.metadata.name}{"\\n"}{end}'], timeout=120)
    assert result.exit_code == 0, result.output
    return sorted(name for name in result.stdout.splitlines() if name.strip())


def secret_data(name: str) -> dict:
    result = kubectl(["-n", "openan", "get", "secret", name, "-o", "json"], timeout=120)
    assert result.exit_code == 0, f"Secret {name} not found: {result.stderr.strip()}"
    return json.loads(result.stdout)["data"]


def secret_uid(name: str) -> str:
    return kubectl_jsonpath(f"secret/{name}", "{.metadata.uid}").stdout.strip()


def volume_secret(deploy: str, volume: str) -> str:
    return kubectl_jsonpath(
        f"deploy/{deploy}", f'{{.spec.template.spec.volumes[?(@.name=="{volume}")].secret.secretName}}'
    ).stdout.strip()


def ingress_annotation(name: str, annotation: str) -> str:
    key = annotation.replace(".", "\\.")
    return kubectl_jsonpath(f"ingress/{name}", f"{{.metadata.annotations.{key}}}").stdout.strip()


def pod_images() -> list[str]:
    result = kubectl(
        ["-n", "openan", "get", "pods", "-o", 'jsonpath={range .items[*]}{.spec.containers[*].image}{"\\n"}{end}'],
        timeout=120,
    )
    assert result.exit_code == 0, result.output
    return sorted(image for image in result.stdout.splitlines() if image.strip())


def pod_image(deploy: str) -> str:
    return kubectl_jsonpath(f"deploy/{deploy}", "{.spec.template.spec.containers[0].image}").stdout.strip()


def hostpath_dirs() -> list[str]:
    result = run(["sudo", "sh", "-c", "ls -d /data/openan-* 2>/dev/null || true"], timeout=60)
    assert result.exit_code == 0, result.output
    return sorted(result.stdout.split())


def configmap_value(name: str, key: str) -> str:
    return kubectl_jsonpath(f"configmap/{name}", f"{{.data.{key}}}").stdout.strip()


def probe_scheme(deploy: str) -> str:
    return kubectl_jsonpath(f"deploy/{deploy}", "{.spec.template.spec.containers[0].livenessProbe.httpGet.scheme}").stdout.strip()


def _delete_probe(pod: str, *, wait: bool) -> None:
    kubectl(["-n", "openan", "delete", "pod", pod, "--ignore-not-found", f"--wait={'true' if wait else 'false'}"],
            timeout=120)


def https_probe(image: str, secret: str, pod: str = PROBE_POD, evidence_stem: str | None = None) -> str:
    """Run the TLS check in a temporary Pod mounting `secret` and return the evidence text."""
    manifest = json.dumps({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": pod, "namespace": "openan"},
        "spec": {
            "restartPolicy": "Never",
            "containers": [{
                "name": "probe",
                "image": image,
                "imagePullPolicy": "IfNotPresent",
                "command": ["python3", "-c", TLS_CHECK, "/ingress-client/ca.crt", REGISTRY_TLS_URL],
                "volumeMounts": [{"name": "ingress-client", "mountPath": "/ingress-client", "readOnly": True}],
            }],
            "volumes": [{"name": "ingress-client", "secret": {"secretName": secret}}],
        },
    })
    _delete_probe(pod, wait=True)
    created = run(["kubectl", "apply", "-f", "-"], stdin=manifest, timeout=120)
    assert created.exit_code == 0, created.output
    try:
        waited = kubectl(
            ["-n", "openan", "wait", "--for=jsonpath={.status.phase}=Succeeded", f"pod/{pod}", "--timeout=240s"],
            timeout=300,
        )
        logs = kubectl(["-n", "openan", "logs", pod], timeout=120)
        details = kubectl(["-n", "openan", "describe", "pod", pod], timeout=120)
    finally:
        _delete_probe(pod, wait=False)
    evidence = (
        f"secret={secret}\nwait exit={waited.exit_code}\n{waited.output}\n"
        f"--- probe logs ---\n{logs.output}\n--- describe ---\n{details.output}"
    )
    if evidence_stem:
        save_evidence(evidence_stem, evidence)
    assert waited.exit_code == 0 and "200" in logs.stdout.split(), (
        f"in-cluster HTTPS access to {REGISTRY_TLS_URL} with the CA from {secret} failed:\n{evidence[-1500:]}"
    )
    return evidence
