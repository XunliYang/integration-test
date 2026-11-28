from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT = 1800
EVIDENCE_DIR = Path(os.getenv("EVIDENCE_DIR", "evidence")).resolve() / "openan-installation"

_SECRET_VALUES: set[str] = set()
_BEARER = re.compile(r"\b(Bearer)\s+[A-Za-z0-9\-._~+/=]{8,}")
_NAMED_SECRET = re.compile(
    r"((?:access_token|refresh_token|api[_-]?key|token_hash|password|passwd)\s*[\"']?\s*[:=]\s*[\"']?)"
    r"([^\s\"',;&}]{4,})",
    re.IGNORECASE,
)

SCENE_COMMANDS = (
    ("ports", ["ss", "-ltnp"]),
    ("pods", ["kubectl", "-n", "openan", "get", "pods", "-o", "wide"]),
    ("pvc", ["kubectl", "-n", "openan", "get", "pvc"]),
    ("events", ["kubectl", "-n", "openan", "get", "events", "--sort-by=.lastTimestamp"]),
    ("helm", ["helm", "ls", "-n", "openan", "--all"]),
    ("logs-registry-center", ["kubectl", "-n", "openan", "logs", "--tail=200", "deploy/registry-center"]),
    ("logs-orchestration-center", ["kubectl", "-n", "openan", "logs", "--tail=200", "deploy/orchestration-center"]),
    ("logs-openan-frontend", ["kubectl", "-n", "openan", "logs", "--tail=200", "deploy/openan-frontend"]),
    ("docker", ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}"]),
)


def register_secret(*values: str) -> None:
    """Declare plaintext values that must never reach evidence files or reports."""
    _SECRET_VALUES.update(value for value in values if value)


def redact(text: str) -> str:
    """Mask registered secrets and credential-looking fields in command output."""
    for value in sorted(_SECRET_VALUES, key=len, reverse=True):
        if len(value) >= 4:
            text = text.replace(value, "***")
    text = _BEARER.sub(r"\1 ***", text)
    return _NAMED_SECRET.sub(r"\1***", text)


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return redact((self.stdout or "") + (self.stderr or ""))


def run(cmd, cwd=None, timeout: int = DEFAULT_TIMEOUT, stdin: str | None = None, env: dict | None = None) -> CommandResult:
    proc = subprocess.run(
        cmd,
        shell=not isinstance(cmd, list),
        cwd=str(cwd) if cwd else None,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )
    return CommandResult(proc.returncode, proc.stdout or "", proc.stderr or "")


def save_evidence(name: str, content: str) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    target = EVIDENCE_DIR / f"{name}.log"
    target.write_text(redact(content), encoding="utf-8", errors="replace")
    return target


def capture_scene(stem: str) -> list[Path]:
    """Save host/cluster state for triage; unavailable tools are skipped."""
    saved = []
    for name, command in SCENE_COMMANDS:
        if shutil.which(command[0]) is None:
            continue
        try:
            result = run(command, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = CommandResult(-1, "", f"{type(exc).__name__}: {exc}")
        saved.append(save_evidence(f"{stem}-scene-{name}", result.output))
    return saved


def run_interactive(
    cmd,
    cwd=None,
    timeout: int = DEFAULT_TIMEOUT,
    answers: list | None = None,
    evidence_stem: str | None = None,
    env: dict | None = None,
) -> CommandResult:
    import pexpect

    answers = list(answers or [])
    # pexpect resolves which(cmd) against the parent cwd, before cwd= is
    # applied to the child; resolve relative script paths ourselves. Skip
    # commands that start with an interpreter (e.g. "bash script.sh").
    if cwd and isinstance(cmd, str) and not os.path.isabs(cmd):
        program, _, arguments = cmd.partition(" ")
        if os.path.dirname(program) and not any(char in program for char in "\"'\\"):
            cmd = str((Path(cwd) / program).resolve()) + (f" {arguments}" if arguments else "")
    child = pexpect.spawn(
        cmd,
        cwd=str(cwd) if cwd else None,
        timeout=90,
        encoding="utf-8",
        codec_errors="replace",
        echo=False,
        env=env,
    )
    # Answers are consumed in order: only the current cursor and the patterns
    # after it are armed, and a hit moves the cursor past that pattern. This is
    # what makes a transcript in which the same prompt text shows up twice (the
    # installer writes the prompt to stderr and the pty echoes the line ending)
    # safe: an already-answered prompt cannot swallow the answer meant for the
    # next one. Questions that the installer skips are handled by arming the
    # rest of the list, so a later pattern may still fire first. The last
    # pattern stays armed once the cursor reaches it, so a retry loop that
    # re-asks the same question keeps receiving its answer.
    cursor = 0
    transcript = []
    deadline = time.monotonic() + timeout
    try:
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError(f"interactive command exceeded timeout: {cmd}")
            armed = answers[cursor:]
            patterns = [pexpect.TIMEOUT, pexpect.EOF]
            for pattern, _ in armed:
                patterns.append(re.compile(pattern, re.IGNORECASE))
            index = child.expect(patterns)
            transcript.append(child.before or "")
            if index == 1:
                break
            if index == 0:
                tail = (child.before or "").strip()
                if tail.endswith(("?", ":", "]")):
                    child.sendline("")
                continue
            hit = index - 2
            cursor += hit + 1 if cursor + hit + 1 < len(answers) else 0
            child.sendline(armed[hit][1])
    finally:
        child.close()
        full = "".join(transcript)
        if evidence_stem:
            save_evidence(evidence_stem, full)
    return CommandResult(child.exitstatus if child.exitstatus is not None else -1, full, "")


def curl_request(
    method: str,
    url: str,
    data: str | None = None,
    headers: list | None = None,
    timeout: int = 60,
    cookie_jar=None,
):
    cmd = ["curl", "-k", "-s", "--max-time", str(timeout), "-X", method, "-w", "\n%{http_code}"]
    for header in headers or []:
        cmd += ["-H", header]
    if data is not None:
        cmd += ["-d", data]
    if cookie_jar is not None:
        cmd += ["-c", str(cookie_jar), "-b", str(cookie_jar)]
    cmd.append(url)
    result = run(cmd, timeout=timeout + 15)
    body, _, status = result.stdout.rpartition("\n")
    return body.strip("\n"), status.strip()


def http_status(url: str, timeout: int = 30) -> str:
    _, status = curl_request("GET", url, timeout=timeout)
    return status


def port_listening(port: int) -> bool:
    result = run(["ss", "-ltnp"])
    return re.search(rf":{port}\b", result.stdout) is not None


_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


def config_value(path, key: str) -> str | None:
    found = None
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, _, value = line.partition("=")
            if name.strip() == key:
                found = value.strip()
    return found


def listening_pids(port: int) -> set[str]:
    pids: set[str] = set()
    for line in run(["ss", "-ltnp"]).stdout.splitlines():
        if re.search(rf":{port}\b", line):
            pids.update(re.findall(r"pid=(\d+)", line))
    return pids


def process_cmdline(pid: str) -> str:
    return run(["ps", "-p", pid, "-o", "cmd="], timeout=60).stdout.strip()


def file_sha256(path) -> str:
    result = run(["sha256sum", str(path)])
    if result.exit_code != 0 or not result.stdout:
        result = run(["sudo", "-n", "sha256sum", str(path)])
    if result.exit_code != 0 or not result.stdout:
        raise RuntimeError(f"cannot hash {path}: {result.output.strip()}")
    return result.stdout.split()[0]


def wait_until(predicate, timeout: int = 300, interval: int = 5):
    deadline = time.monotonic() + timeout
    result = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
        except Exception:
            result = None
        if result:
            return result
        time.sleep(interval)
    return result


def kubectl(args: list, timeout: int = 600) -> CommandResult:
    return run(["kubectl"] + args, timeout=timeout)


def kubectl_jsonpath(resource: str, jsonpath: str, namespace: str = "openan") -> CommandResult:
    return kubectl(["-n", namespace, "get", resource, "-o", f"jsonpath={jsonpath}"])
