from pathlib import Path
import tomllib

from aiusagetracker import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_release_versions_match():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__
    assert f'version-{__version__}-' in (ROOT / "README.md").read_text(encoding="utf-8")
    assert f'#define MyAppVersion "{__version__}"' in (ROOT / "installer.iss").read_text()
    assert f"StringStruct('ProductVersion', '{__version__}')" in (ROOT / "assets/windows-version.txt").read_text()


def test_packaging_preserves_the_spec_and_worker_guard():
    build = (ROOT / "build.ps1").read_text()
    assert "*.spec" not in build
    assert "AIUsageTracker.spec" in build
    spec = (ROOT / "AIUsageTracker.spec").read_text()
    assert "runtime_hooks=['assets/runtime_hook_mp.py']" in spec
    assert "'argparse'" not in spec
    assert "('LICENSE', '.')" in spec
    entry = (ROOT / "run.py").read_text()
    assert entry.index("freeze_support()") < entry.index("from aiusagetracker")


def test_runtime_requirements_match_project_metadata():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    listed = (ROOT / "requirements.txt").read_text().splitlines()
    assert listed == project["project"]["dependencies"]
