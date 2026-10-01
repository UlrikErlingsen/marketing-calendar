"""Architecture rules for Signal Hub: the core package is UI-free (only ``seasonsignal/ui/`` may import
Streamlit) and storage sits behind one module."""

import ast
from pathlib import Path

import seasonsignal

SRC = Path(__file__).parents[1] / "src"
PACKAGE = SRC / "seasonsignal"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_no_file_under_src_imports_streamlit_except_ui():
    ui = PACKAGE / "ui"
    offenders = [
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.py")
        if ui not in path.parents
        and any(name == "streamlit" or name.startswith("streamlit.") for name in _imports(path))
    ]
    assert not offenders, f"streamlit imported under src/ outside seasonsignal/ui/: {offenders}"


def test_core_package_does_not_import_the_ui():
    for path in PACKAGE.glob("*.py"):
        assert not any(name.startswith("seasonsignal.ui") for name in _imports(path)), path.name
        assert "from .ui" not in path.read_text(encoding="utf-8"), path.name


def test_only_storage_module_touches_the_filesystem_for_state():
    for path in PACKAGE.glob("*.py"):
        if path.name == "storage.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert "write_text(" not in source and "json.dump" not in source, path.name
        assert "sqlite3" not in source, path.name


def test_public_api_is_complete():
    for name in seasonsignal.__all__:
        assert hasattr(seasonsignal, name), name
    for name in ("load_library", "plan_back", "build_ics", "build_xlsx", "load_store", "save_store", "__version__"):
        assert name in seasonsignal.__all__


def test_moments_library_ships_with_the_package():
    assert (PACKAGE / "moments" / "no.yaml").exists()
    pyproject = (SRC.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert 'seasonsignal = ["moments/*.yaml"]' in pyproject
    assert '"seasonsignal.ui" = ["assets/marks/*"]' in pyproject
    assert (PACKAGE / "ui" / "assets" / "marks" / "seasonsignal-mark-64.png").exists()
