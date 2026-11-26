from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import pytest

from utils.env import PROFILES, install_config, load_env

LOG_DIR = Path(__file__).resolve().parents[1] / "evidence" / "openan-installation"
LOG_FILE = LOG_DIR / "test-run.log"

MARKER_NAMES = [
    "openan-installation",
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
]


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


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report):
    if report.when == "call":
        outcome = "PASSED" if report.passed else "FAILED" if report.failed else "SKIPPED"
        log.info("%s %s (%.1fs)", outcome, report.nodeid, report.duration)
    elif report.when == "setup" and report.skipped:
        reason = report.longreprtext.splitlines()[-1] if hasattr(report, 'longreprtext') else ''
        log.info("SKIPPED %s: %s", report.nodeid, reason[:120])


def pytest_sessionfinish(session):
    elapsed = time.time() - _session_start if _session_start else 0
    log.info("TEST SESSION END  elapsed=%.1fs  collected=%d", elapsed, _total_items)


@pytest.fixture(scope="session", autouse=True)
def install_env():
    load_env()
    cfg = install_config()
    log.info("profile=%s repo=%s", cfg.machine_profile, cfg.repo_path)
    return cfg


@pytest.fixture(scope="session")
def require_profile(install_env):
    def _require(*profiles):
        if install_env.machine_profile not in profiles:
            pytest.skip(f"host profile {install_env.machine_profile} does not match required {list(profiles)}")

    return _require
