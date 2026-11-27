from __future__ import annotations

import logging

from utils.env import InstallConfig
from utils.shell import CommandResult, http_status, run, run_interactive, wait_until

log = logging.getLogger("openan-e2e.binary")

# The binary registry-center has no /health route; its FastAPI app only exposes
# /rest/v1/registry-center/* (openapi/docs disabled). The query endpoint returns
# 200 with an empty list when the service is up and reachable.
REGISTRY_BASE = "http://127.0.0.1:5000"
REGISTRY_UP = f"{REGISTRY_BASE}/rest/v1/registry-center/agent-cards"
ORCHESTRATION_UP = "https://127.0.0.1/api/orchestrate/rest/v1/orchestrate/templates"

# orchestration-center v1.0.0 samples.start_agents_server binds one port per
# sample agent card (8899-8907, 26335, 26336); uninstall.sh also scans 8080.
SAMPLE_AGENTS_PORTS = (26335, 26336, *range(8899, 8908))

UNINSTALL_PORTS = (5000, 5001, 8080, *SAMPLE_AGENTS_PORTS)

DEFAULT_ANSWERS = [
    (r"Skip LLM configuration and configure manually\?", "y"),
    (r"Start sample agents server\?", "n"),
]

SAMPLE_ANSWERS = [
    (r"Skip LLM configuration and configure manually\?", "y"),
    (r"Start sample agents server\?", "y"),
]


def binary_answers(*, registry_url: str | None = None, start_sample: bool = False) -> list:
    answers = list(SAMPLE_ANSWERS if start_sample else DEFAULT_ANSWERS)
    if registry_url:
        answers.insert(1, (r"Enter registry center URL \[", registry_url))
    return answers


def wait_registry_up(timeout: int = 120) -> None:
    # The install script backgrounds uvicorn and exits before it is listening;
    # poll until the query endpoint answers 200.
    assert wait_until(lambda: http_status(REGISTRY_UP) == "200", timeout=timeout), REGISTRY_UP


def wait_orchestration_up(timeout: int = 120) -> None:
    assert wait_until(lambda: http_status(ORCHESTRATION_UP) == "200", timeout=timeout), ORCHESTRATION_UP


RUNTIME_PROBE = (
    'for c in python3.12 python3; do command -v "$c" >/dev/null 2>&1 && echo "python $c $("$c" --version 2>&1)"; done;'
    ' command -v node >/dev/null 2>&1 && echo "node $(node --version 2>&1)"; true'
)


def _meets(version: str, major: int, minor: int, *, exact_major: bool = False) -> bool:
    parts = version.split(".")
    try:
        found = (int(parts[0]), int(parts[1]))
    except (IndexError, ValueError):
        return False
    if exact_major:
        return found[0] == major and found[1] >= minor
    return found >= (major, minor)


def parse_host_runtimes(probe_output: str) -> dict:
    runtimes = {"python": None, "node": None}
    for line in probe_output.splitlines():
        name, _, rest = line.partition(" ")
        if name == "python" and runtimes["python"] is None:
            command, _, raw = rest.partition(" ")
            fields = raw.split()
            if len(fields) > 1 and _meets(fields[1], 3, 12, exact_major=True):
                runtimes["python"] = (command, fields[1])
        elif name == "node" and runtimes["node"] is None:
            version = rest.replace("v", "", 1)
            if _meets(version, 20, 19):
                runtimes["node"] = version
    return runtimes


def host_runtimes() -> dict:
    """Runtimes install.sh reuses instead of installing: {"python": (command, version) | None, "node": version | None}."""
    runtimes = parse_host_runtimes(run(RUNTIME_PROBE, timeout=60).stdout)
    python = runtimes["python"]
    log.info("host runtimes before install: python=%s node=%s", f"{python[1]} ({python[0]})" if python else "none", runtimes["node"] or "none")
    return runtimes


def run_binary_script(
    cfg: InstallConfig,
    script: str,
    *arguments: str,
    answers: list | None = None,
    evidence_stem: str | None = None,
) -> CommandResult:
    command = " ".join((f"./{script}", *arguments))
    return run_interactive(
        command,
        cwd=cfg.binary_dir,
        answers=answers or [],
        evidence_stem=evidence_stem,
    )


def install_binary(
    cfg: InstallConfig,
    *flags: str,
    answers: list | None = None,
    evidence_stem: str | None = None,
) -> CommandResult:
    return run_binary_script(
        cfg,
        "install.sh",
        *flags,
        answers=DEFAULT_ANSWERS if answers is None else answers,
        evidence_stem=evidence_stem,
    )


def uninstall_binary(cfg: InstallConfig) -> CommandResult:
    return run("./uninstall.sh --force", cwd=cfg.binary_dir, timeout=600)


def configure_llm_interactive(cfg: InstallConfig, model: str, url: str, api_key: str, *targets: str) -> CommandResult:
    answers = [
        (r"Enter LLM model name", model),
        (r"Enter LLM API URL", url),
        (r"Enter (?:your API key|API key \[\*\*\*\])", api_key),
    ]
    return run_binary_script(cfg, "configure_llm.sh", *(targets or ("--reg",)), answers=answers)
