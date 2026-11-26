from __future__ import annotations

from utils.env import InstallConfig
from utils.shell import CommandResult, http_status, run, run_interactive, wait_until

# The binary registry-center has no /health route; its FastAPI app only exposes
# /rest/v1/registry-center/* (openapi/docs disabled). The query endpoint returns
# 200 with an empty list when the service is up and reachable.
REGISTRY_UP = "http://127.0.0.1:5000/rest/v1/registry-center/agent-cards"

SAMPLE_AGENTS_PORTS = (8080, 26335, 26336, *range(8899, 8908))

DEFAULT_ANSWERS = [
    (r"Skip LLM configuration and configure manually\?", "y"),
    (r"Start sample agents server\?", "n"),
]

SAMPLE_ANSWERS = [
    (r"Skip LLM configuration and configure manually\?", "y"),
    (r"Start sample agents server\?", "y"),
]


def wait_registry_up(timeout: int = 120) -> None:
    # The install script backgrounds uvicorn and exits before it is listening;
    # poll until the query endpoint answers 200.
    assert wait_until(lambda: http_status(REGISTRY_UP) == "200", timeout=timeout), REGISTRY_UP


def install_binary(
    cfg: InstallConfig,
    *flags: str,
    answers: list | None = None,
    evidence_stem: str | None = None,
) -> CommandResult:
    command = " ".join(("./install.sh", *flags))
    return run_interactive(
        command,
        cwd=cfg.binary_dir,
        answers=DEFAULT_ANSWERS if answers is None else answers,
        evidence_stem=evidence_stem,
    )


def uninstall_binary(cfg: InstallConfig) -> CommandResult:
    return run("./uninstall.sh --force", cwd=cfg.binary_dir, timeout=600)
