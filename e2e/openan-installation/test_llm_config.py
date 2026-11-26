import os

import pytest

from utils.binary_install import install_binary, uninstall_binary
from utils.env import install_config
from utils.shell import redact, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.P0,
    pytest.mark.smoke,
]


@getattr(pytest.mark, "FIT-openan-installation-llm-config-001")
@getattr(pytest.mark, "26-winter")
def test_valid_llm_config_written_after_validation(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    if not (cfg.llm_model and cfg.llm_api_url and cfg.llm_api_key):
        pytest.skip("OPENAN_INSTALL_LLM_MODEL / _API_URL / _API_KEY are not configured")
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, "--reg")
    assert install.exit_code == 0, install.output
    # configure_llm.sh writes to <svc>/common/config/llm_config.json
    llm_config_path = cfg.binary_dir / "registry-center" / "common" / "config" / "llm_config.json"
    backup = llm_config_path.read_text() if llm_config_path.is_file() else None
    configure = run(
        [
            "./configure_llm.sh",
            "--reg",
            "--model",
            cfg.llm_model,
            "--url",
            cfg.llm_api_url,
        ],
        cwd=cfg.binary_dir,
        timeout=180,
        env={**os.environ, "LLM_API_KEY": cfg.llm_api_key},
    )
    assert configure.exit_code == 0, configure.output
    assert "LLM configuration complete" in configure.output, configure.output
    assert llm_config_path.is_file(), f"llm_config.json not found at {llm_config_path}"
    content = llm_config_path.read_text()
    assert cfg.llm_model in content, redact(content)
    assert cfg.llm_api_url in content, redact(content)
    if backup is not None:
        llm_config_path.write_text(backup)
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
