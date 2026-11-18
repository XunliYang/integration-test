import pytest

from utils.env import install_config
from utils.shell import run, run_interactive

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    pytest.mark.online,
    getattr(pytest.mark, "registry-center"),
    pytest.mark.P0,
    pytest.mark.smoke,
]

LLM_SKIP = [(r"llm", "y")]


def test_valid_llm_config_written_after_validation(require_profile):
    require_profile("online-vm")
    cfg = install_config()
    if not (cfg.llm_model and cfg.llm_api_url and cfg.llm_api_key):
        pytest.skip("OPENAN_INSTALL_LLM_MODEL / _API_URL / _API_KEY are not configured")
    install = run_interactive("./install.sh --reg", cwd=cfg.binary_dir, answers=LLM_SKIP)
    assert install.exit_code == 0, install.output
    llm_config_path = cfg.binary_dir / "registry-center" / "llm_config.json"
    backup = llm_config_path.read_text() if llm_config_path.is_file() else None
    configure = run(
        [
            "./configure_llm.sh",
            "--reg",
            "--model",
            cfg.llm_model,
            "--url",
            cfg.llm_api_url,
            "--api-key",
            cfg.llm_api_key,
        ],
        cwd=cfg.binary_dir,
        timeout=180,
    )
    assert configure.exit_code == 0, configure.output
    assert llm_config_path.is_file(), f"llm_config.json not found at {llm_config_path}"
    content = llm_config_path.read_text()
    assert cfg.llm_model in content, content
    assert cfg.llm_api_url in content, content
    if backup is not None:
        llm_config_path.write_text(backup)
    uninstall = run("./uninstall.sh --force", cwd=cfg.binary_dir, timeout=600)
    assert uninstall.exit_code == 0, uninstall.output
