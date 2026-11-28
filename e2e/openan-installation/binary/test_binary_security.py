import pytest

from utils.binary_install import configure_llm_interactive, install_binary, uninstall_binary
from utils.env import install_config

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    pytest.mark.P1,
    pytest.mark.full,
]


def _masked(api_key: str) -> str:
    if len(api_key) > 8:
        return f"{api_key[:4]}...{api_key[-4:]}"
    return "***"


@getattr(pytest.mark, "DFX-openan-installation-security-001")
@getattr(pytest.mark, "26-winter")
def test_api_key_input_is_masked_and_never_echoed_in_full(require_profile, cleanup):
    require_profile("online-vm")
    cfg = install_config()
    if not (cfg.llm_model and cfg.llm_api_url and cfg.llm_api_key):
        pytest.skip("OPENAN_INSTALL_LLM_MODEL / _API_URL / _API_KEY are not configured")
    cleanup.add("binary uninstall", uninstall_binary, cfg)
    install = install_binary(cfg, "--reg")
    assert install.exit_code == 0, install.output
    llm_config = cfg.binary_dir / "registry-center" / "common" / "config" / "llm_config.json"
    backup = llm_config.read_text() if llm_config.is_file() else None
    result = configure_llm_interactive(cfg, cfg.llm_model, cfg.llm_api_url, cfg.llm_api_key)
    assert result.exit_code == 0, result.output
    raw = result.stdout
    leaked = cfg.llm_api_key in raw
    assert not leaked, "API key plaintext appears in the captured script output"
    assert "*" * len(cfg.llm_api_key) in raw, "API key input is not echoed as one asterisk per character"
    assert f"key={_masked(cfg.llm_api_key)}" in raw, "masked key form missing from the script output"
    key_written = cfg.llm_api_key in llm_config.read_text()
    assert key_written, f"{llm_config} does not contain the entered API key"
    if backup is not None:
        llm_config.write_text(backup)
        assert llm_config.read_text() == backup, f"{llm_config} was not restored"
    uninstall = uninstall_binary(cfg)
    assert uninstall.exit_code == 0, uninstall.output
