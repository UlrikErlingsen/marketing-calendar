"""Season Signal is in the suite's small-input tier: one 50 MB upload cap, the same everywhere it is set."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CAP_MB = 50


def test_streamlit_config_sets_the_small_input_cap() -> None:
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert re.search(r"^maxUploadSize = (\d+)$", config, re.MULTILINE).group(1) == str(CAP_MB)


def test_launchers_pass_the_cap_and_accept_an_override() -> None:
    bat = (ROOT / "run_app.bat").read_text(encoding="utf-8")
    assert f"set SEASONSIGNAL_MAX_UPLOAD_MB={CAP_MB}" in bat
    assert "--server.maxUploadSize=%SEASONSIGNAL_MAX_UPLOAD_MB%" in bat
    command = (ROOT / "run_app.command").read_text(encoding="utf-8")
    assert f'--server.maxUploadSize="${{SEASONSIGNAL_MAX_UPLOAD_MB:-{CAP_MB}}}"' in command


def test_docker_sets_the_cap_by_environment_only() -> None:
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert f"STREAMLIT_SERVER_MAX_UPLOAD_SIZE={CAP_MB}" in docker
    assert "--server.maxUploadSize" not in docker


def test_no_in_code_upload_path_needs_its_own_limit() -> None:
    # The plan is typed in, not uploaded; if an uploader is ever added it needs limits consistent with CAP_MB.
    sources = [path for path in (ROOT / "src" / "seasonsignal").rglob("*.py") if path.name != "signal_theme.py"]
    assert sources
    assert not [path.name for path in sources if "file_uploader" in path.read_text(encoding="utf-8")]
