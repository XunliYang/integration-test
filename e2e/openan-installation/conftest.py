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


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    log.info("START %s", item.nodeid)


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item):
    log.info("END   %s", item.nodeid)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report):
    if report.when == "call":
        outcome = "PASSED" if report.passed else "FAILED" if report.failed else "SKIPPED"
        log.info("%s %s (%.1fs)", outcome, report.nodeid, report.duration)
    elif report.when == "setup" and report.skipped:
        log.info("SKIPPED %s: %s", report.nodeid, report.longreprtext[:100] if hasattr(report, 'longreprtext') else '')


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
