from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT = 1800
EVIDENCE_DIR = Path(os.getenv("EVIDENCE_DIR", "evidence")).resolve() / "openan-installation"


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return (self.stdout or "") + (self.stderr or "")


def run(cmd, cwd=None, timeout: int = DEFAULT_TIMEOUT, stdin: str | None = None) -> CommandResult:
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
    )
    return CommandResult(proc.returncode, proc.stdout or "", proc.stderr or "")


def save_evidence(name: str, content: str) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    target = EVIDENCE_DIR / f"{name}.log"
    target.write_text(content, encoding="utf-8", errors="replace")
    return target


def run_interactive(
    cmd,
    cwd=None,
    timeout: int = DEFAULT_TIMEOUT,
    answers: list | None = None,
    evidence_stem: str | None = None,
) -> CommandResult:
    import pexpect

    answers = list(answers or [])
    # pexpect resolves which(cmd) against the parent cwd, before cwd= is
    # applied to the child; resolve relative paths ourselves.
    if cwd and isinstance(cmd, str) and not os.path.isabs(cmd) and os.path.dirname(cmd):
        cmd = str((Path(cwd) / cmd).resolve())
    child = pexpect.spawn(
        cmd,
        cwd=str(cwd) if cwd else None,
        timeout=90,
        encoding="utf-8",
        codec_errors="replace",
    )
    patterns = [pexpect.TIMEOUT, pexpect.EOF]
    for pattern, _ in answers:
        patterns.append(re.compile(pattern, re.IGNORECASE))
    transcript = []
    deadline = time.monotonic() + timeout
    try:
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError(f"interactive command exceeded timeout: {cmd}")
            index = child.expect(patterns)
            transcript.append(child.before or "")
            if index == 1:
                break
            if index == 0:
                tail = (child.before or "").strip()
                if tail.endswith(("?", ":", "]")):
                    child.sendline("")
                continue
            child.sendline(answers[index - 2][1])
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
    use_client_certs: bool = False,
    cookie_jar=None,
):
    cmd = ["curl", "-k", "-s", "--max-time", str(timeout), "-X", method, "-w", "\n%{http_code}"]
    for header in headers or []:
        cmd += ["-H", header]
    if data is not None:
        cmd += ["-d", data]
    if cookie_jar is not None:
        cmd += ["-c", str(cookie_jar), "-b", str(cookie_jar)]
    if use_client_certs:
        cert = os.getenv("REGISTRY_CLIENT_CERT", "").strip()
        key = os.getenv("REGISTRY_CLIENT_KEY", "").strip()
        if cert and key:
            cmd += ["--cert", cert, "--key", key]
    cmd.append(url)
    result = run(cmd, timeout=timeout + 15)
    body, _, status = result.stdout.rpartition("\n")
    return body.strip("\n"), status.strip()


def http_status(url: str, timeout: int = 30) -> str:
    _, status = curl_request("GET", url, timeout=timeout)
    return status


def port_listening(port: int) -> bool:
    result = run(["ss", "-ltn"])
    return re.search(rf":{port}\b", result.stdout) is not None


def file_sha256(path) -> str | None:
    result = run(["sha256sum", str(path)])
    if result.exit_code != 0 or not result.stdout:
        return None
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
