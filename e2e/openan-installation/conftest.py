from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

# Test modules live in per-installation-line subdirectories; put the package
# root on sys.path so `from utils...` works regardless of the import mode.
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import utils.env as _utils_env

if Path(_utils_env.__file__).resolve().parent != HERE / "utils":
    raise ImportError(
        "another feature package's `utils` is already imported; "
        "run one feature directory per pytest invocation"
    )

from utils.env import InstallConfigError, install_config, load_env
from utils.shell import capture_scene, register_secret, save_evidence

LOG_DIR = HERE.parent / "evidence" / "openan-installation"
LOG_FILE = LOG_DIR / "test-run.log"

CASE_IDS = (
    "FIT-openan-installation-binary-install-001",
    "FIT-openan-installation-binary-components-001",
    "FIT-openan-installation-llm-config-001",
    "FIT-openan-installation-helm-online-001",
    "FIT-openan-installation-helm-components-001",
    "FIT-openan-installation-offline-k8s-001",
    "FIT-openan-installation-offline-compose-001",
    "DFX-openan-installation-testability-001",
    "DFX-openan-installation-serviceability-001",
    "DFX-openan-installation-serviceability-003",
    "DFX-openan-installation-reliability-001",
    "DFX-openan-installation-security-002",
    "FIT-openan-installation-binary-regurl-001",
    "FIT-openan-installation-binary-filestore-001",
    "FIT-openan-installation-binary-offline-001",
    "FIT-openan-installation-local-build-001",
    "DFX-openan-installation-testability-002",
    "DFX-openan-installation-reliability-003",
    "DFX-openan-installation-security-001",
    "FIT-openan-installation-helm-values-001",
    "FIT-openan-installation-db-type-001",
    "FIT-openan-installation-db-type-002",
    "FIT-openan-installation-db-type-003",
    "DFX-openan-installation-diagnosability-002",
    "DFX-openan-installation-serviceability-007",
    "DFX-openan-installation-reliability-002",
    "DFX-openan-installation-reliability-004",
    "DFX-openan-installation-reliability-005",
    "FIT-openan-installation-offline-k8s-002",
    "DFX-openan-installation-diagnosability-001",
    "DFX-openan-installation-serviceability-002",
    "DFX-openan-installation-serviceability-005",
    "DFX-openan-installation-serviceability-006",
    "DFX-openan-installation-serviceability-008",
    "DFX-openan-installation-security-003",
    "DFX-openan-installation-security-006",
    "FIT-openan-installation-binary-regurl-002",
    "FIT-openan-installation-llm-config-002",
    "FIT-openan-installation-compose-db-001",
    "FIT-openan-installation-binary-sample-001",
    "FIT-openan-installation-binary-version-001",
    "FIT-openan-installation-frontend-select-001",
    "FIT-openan-installation-local-build-002",
    "DFX-openan-installation-serviceability-004",
    "DFX-openan-installation-performance-001",
    "DFX-openan-installation-security-004",
    "DFX-openan-installation-security-005",
    "DFX-openan-installation-compatibility-001",
    "DFX-openan-installation-compatibility-002",
    "DFX-openan-installation-compatibility-003",
    "FIT-openan-installation-binary-pack-001",
)

MARKER_NAMES = [
    "openan-installation",
    "26-winter",
    "online",
    "offline",
    "with-workload-cluster",
    "registry-center",
    "orchestration-center",
    "openan-frontend",
    "openan-postgres",
    "P0",
    "P1",
    "P2",
    "smoke",
    "full",
    "slow",
    "skip-temporarily",
    *CASE_IDS,
]

REPO_PROFILES = ("online-vm", "cluster-ops")


def _setup_logging():
    """File + console logging so a detached run still leaves a readable trace."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("openan-e2e")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # avoid duplicate console lines via the root logger
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                            datefmt="%H:%M:%S")
    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


log = _setup_logging()


def pytest_configure(config):
    for name in MARKER_NAMES:
        config.addinivalue_line("markers", f"{name}: openan-installation test package label")


# ---- progress + detailed log into test-run.log -------------------------

_session_start = None
_collected_items = []
_total_items = 0
_outcomes = {"passed": 0, "failed": 0, "errored": 0, "skipped": 0}
_dirty_cleanups = []


def pytest_sessionstart(session):
    global _session_start
    _session_start = time.time()
    log.info("=" * 60)
    log.info("TEST SESSION START")
    _collected_items.clear()


def pytest_collection_finish(session):
    global _total_items
    _total_items = len(session.items)
    _collected_items.extend(session.items)
    log.info("collected %d items", _total_items)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    idx = _collected_items.index(item) + 1 if item in _collected_items else 0
    pct = (idx / _total_items * 100) if _total_items else 0
    log.info("[%3d%%] START %s", pct, item.nodeid)


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item):
    log.info("END   %s", item.nodeid)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report):
    if report.when == "call":
        outcome = "passed" if report.passed else "failed" if report.failed else "skipped"
        log.info("%s %s (%.1fs)", outcome.upper(), report.nodeid, report.duration)
    elif report.when == "setup" and report.skipped:
        outcome = "skipped"
        reason = report.longreprtext.splitlines()[-1] if hasattr(report, 'longreprtext') else ''
        log.info("SKIPPED %s: %s", report.nodeid, reason[:120])
    elif report.when == "setup" and report.failed:
        outcome = "errored"
        log.info("ERROR %s at setup", report.nodeid)
    elif report.when == "teardown" and report.failed:
        log.error("ERROR %s at teardown", report.nodeid)
        return
    else:
        return
    _outcomes[outcome] += 1


def pytest_sessionfinish(session):
    elapsed = time.time() - _session_start if _session_start else 0
    log.info(
        "TEST SESSION END  elapsed=%.1fs  collected=%d  passed=%d failed=%d errored=%d skipped=%d",
        elapsed, _total_items,
        _outcomes["passed"], _outcomes["failed"], _outcomes["errored"], _outcomes["skipped"],
    )
    if _dirty_cleanups:
        log.error("HOST LEFT DIRTY BY FAILED CLEANUP: %s", "; ".join(_dirty_cleanups))


@pytest.fixture(scope="session", autouse=True)
def install_env():
    load_env()
    cfg = install_config()
    if cfg.machine_profile in REPO_PROFILES and cfg.repo_path is None:
        raise InstallConfigError(
            "OPENAN_INSTALL_REPO_PATH is not set (required by online-vm and cluster-ops cases)"
        )
    register_secret(cfg.llm_api_key, cfg.admin_password, cfg.db_password)
    log.info("profile=%s repo=%s", cfg.machine_profile, cfg.repo_path)
    return cfg


@pytest.fixture(scope="session")
def require_profile(install_env):
    def _require(*profiles):
        if install_env.machine_profile not in profiles:
            pytest.skip(f"host profile {install_env.machine_profile} does not match required {list(profiles)}")

    return _require


@pytest.fixture
def require_repo(install_env):
    def _require() -> None:
        if install_env.repo_path is None:
            pytest.skip("OPENAN_INSTALL_REPO_PATH is not set")

    return _require


@pytest.fixture
def require_opt_in():
    def _require(enabled: bool, reason: str) -> None:
        if not enabled:
            pytest.skip(reason)

    return _require


class CleanupPlan:
    def __init__(self) -> None:
        self._steps = []

    def add(self, label, step, *args, **kwargs) -> None:
        self._steps.append((label, lambda: step(*args, **kwargs)))

    def run(self, stem: str) -> list[str]:
        dirty = []
        for index, (label, step) in enumerate(reversed(self._steps), 1):
            started = time.time()
            try:
                result = step()
                exit_code = getattr(result, "exit_code", 0)
                output = getattr(result, "output", "")
            except Exception as exc:
                exit_code, output = -1, f"{type(exc).__name__}: {exc}"
            save_evidence(f"{stem}-cleanup-{index}", f"[{label}] exit={exit_code}\n{output}")
            log.info("CLEANUP %s exit=%s elapsed=%.1fs", label, exit_code, time.time() - started)
            if exit_code != 0:
                dirty.append(label)
        return dirty


@pytest.fixture
def cleanup(request):
    """Uninstall steps (LIFO) run only when the case fails; a passing case has asserted its own uninstall."""
    plan = CleanupPlan()
    yield plan
    failed = any(
        report is not None and report.failed
        for report in (getattr(request.node, "rep_setup", None), getattr(request.node, "rep_call", None))
    )
    if not failed:
        return
    stem = request.node.name
    for path in capture_scene(stem):
        log.info("SCENE %s", path)
    _dirty_cleanups.extend(f"{stem}: {label}" for label in plan.run(stem))
