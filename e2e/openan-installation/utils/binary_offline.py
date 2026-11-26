from __future__ import annotations

from pathlib import Path

from utils.env import InstallConfig
from utils.shell import CommandResult, run, run_interactive, strip_ansi

DEFAULT_ANSWERS = [
    (r"Skip LLM configuration and configure manually\?", "y"),
    (r"Overwrite\? \(y/n\): ", "y"),
    (r"Start sample agents server\?", "n"),
]


def offline_dir(cfg: InstallConfig) -> Path:
    import pytest

    if not cfg.binary_offline_dir:
        pytest.skip("OPENAN_INSTALL_BINARY_OFFLINE_DIR is not set")
    directory = Path(cfg.binary_offline_dir)
    for script in ("install.sh", "uninstall.sh"):
        if not (directory / script).is_file():
            pytest.fail(f"{script} is missing in {directory}")
    return directory


def install_binary_offline(
    directory: Path,
    *flags: str,
    answers: list | None = None,
    evidence_stem: str | None = None,
) -> CommandResult:
    command = " ".join(("./install.sh", *flags))
    result = run_interactive(
        command,
        cwd=directory,
        answers=DEFAULT_ANSWERS if answers is None else answers,
        timeout=3600,
        evidence_stem=evidence_stem,
    )
    return CommandResult(result.exit_code, strip_ansi(result.stdout), result.stderr)


def uninstall_binary_offline(directory: Path) -> CommandResult:
    result = run("./uninstall.sh --force", cwd=directory, timeout=600)
    return CommandResult(result.exit_code, strip_ansi(result.stdout), result.stderr)


def component_dirs(directory: Path, prefix: str) -> list[Path]:
    return sorted(path for path in directory.glob(f"{prefix}-*") if path.is_dir())
