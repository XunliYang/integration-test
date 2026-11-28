import os

import pytest

from utils.binary_install import install_binary, run_binary_script, uninstall_binary
from utils.env import install_config
from utils.shell import redact, run

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.full,
]


@getattr(pytest.mark, "FIT-openan-installation-llm-config-001")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P0
@pytest.mark.smoke
def test_valid_llm_config_written_after_validation(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    if not (cfg.llm_model and cfg.llm_api_url and cfg.llm_api_key):
        pytest.skip("OPENAN_INSTALL_LLM_MODEL / _API_URL / _API_KEY are not configured")
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, "--reg")
    assert install.exit_code == 0, install.output
    llm_config = cfg.binary_dir / "registry-center" / "common" / "config" / "llm_config.json"
    backup = llm_config.read_text() if llm_config.is_file() else None
    configure = run(
        ["./configure_llm.sh", "--reg", "--model", cfg.llm_model, "--url", cfg.llm_api_url],
        cwd=cfg.binary_dir,
        timeout=180,
        env={**os.environ, "LLM_API_KEY": cfg.llm_api_key},
    )
    assert configure.exit_code == 0, configure.output
    assert "LLM configuration complete" in configure.output, configure.output
    assert llm_config.is_file(), f"llm_config.json not found at {llm_config}"
    content = llm_config.read_text()
    assert cfg.llm_model in content, redact(content)
    assert cfg.llm_api_url in content, redact(content)
    if backup is not None:
        llm_config.write_text(backup)
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output


@getattr(pytest.mark, "FIT-openan-installation-llm-config-002")
@getattr(pytest.mark, "26-winter")
@pytest.mark.P2
@pytest.mark.full
def test_invalid_llm_endpoint_fails_validation_with_retry_prompt(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, "--reg")
    assert install.exit_code == 0, install.output
    llm_config = cfg.binary_dir / "registry-center" / "common" / "config" / "llm_config.json"
    backup = llm_config.read_text() if llm_config.is_file() else None
    configure = run_binary_script(
        cfg,
        "configure_llm.sh",
        "--reg",
        answers=[
            (r"Enter LLM model name", "e2e-invalid-endpoint"),
            (r"Enter LLM API URL", "http://127.0.0.1:1/invalid"),
            (r"Enter your API key", "e2e-key"),
            (r"Model \[", "skip"),
        ],
        evidence_stem="llm-config-002",
    )
    assert configure.exit_code == 0, configure.output
    assert "[ERROR] Cannot connect to http://127.0.0.1:1/invalid/chat/completions." in configure.output, configure.output[-2000:]
    assert "[RETRY] Please re-enter LLM configuration." in configure.output, configure.output[-2000:]
    assert "[WARN] Validation skipped. The configuration may not work correctly." in configure.output, configure.output[-2000:]
    content = llm_config.read_text()
    assert "e2e-invalid-endpoint" in content and "http://127.0.0.1:1/invalid" in content, redact(content)
    if backup is not None:
        llm_config.write_text(backup)
        assert llm_config.read_text() == backup, f"{llm_config} was not restored"
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
