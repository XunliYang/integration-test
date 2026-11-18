from __future__ import annotations

import pytest

from utils.env import PROFILES, install_config, load_env

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


def pytest_configure(config):
    for name in MARKER_NAMES:
        config.addinivalue_line("markers", f"{name}: openan-installation test package label")


@pytest.fixture(scope="session", autouse=True)
def install_env():
    load_env()
    return install_config()


@pytest.fixture(scope="session")
def require_profile(install_env):
    def _require(*profiles):
        if install_env.machine_profile not in profiles:
            pytest.skip(f"host profile {install_env.machine_profile} does not match required {list(profiles)}")

    return _require
