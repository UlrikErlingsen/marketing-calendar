"""Season Signal has no built-in data limits; the suite's 10,000 MB Streamlit upload cap is the same everywhere."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CAP_MB = 10_000


def test_streamlit_config_sets_the_suite_upload_cap() -> None:
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
    # The plan is typed in, not uploaded, so no demo caps are needed (Signal Hub APP_CONTRACT section 9). If an uploader
    # is ever added, give it a limits module: unbounded locally, capped only with SIGNAL_PUBLIC=1.
    sources = [path for path in (ROOT / "src" / "seasonsignal").rglob("*.py") if path.name != "signal_theme.py"]
    assert sources
    assert not [path.name for path in sources if "file_uploader" in path.read_text(encoding="utf-8")]
