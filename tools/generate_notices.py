#!/usr/bin/env python3
"""Collect bundled runtime license texts from the installed build environment."""
from importlib import metadata
import ast
from pathlib import Path
import re
import sys

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
names = set()
pending = [Requirement(line) for line in (ROOT / "requirements.txt").read_text().splitlines()
           if line and not line.startswith("#")]
while pending:
    requirement = pending.pop()
    if requirement.marker and not requirement.marker.evaluate():
        continue
    name = requirement.name.lower().replace("_", "-")
    if name in names:
        continue
    names.add(name)
    distribution = metadata.distribution(name)
    pending.extend(Requirement(value) for value in distribution.requires or [])

names.add("pyinstaller")
analysis = ROOT / "build/AIUsageTracker/Analysis-00.toc"
if analysis.exists():
    package_map = metadata.packages_distributions()

    def collect_bundled(value):
        if isinstance(value, (list, tuple)):
            for child in value:
                collect_bundled(child)
        elif isinstance(value, str) and "site-packages" in value:
            parts = value.replace("\\", "/").split("site-packages/", 1)
            if len(parts) == 2:
                module = parts[1].split("/", 1)[0].split(".")[0]
                names.update(package_map.get(module, []))

    collect_bundled(ast.literal_eval(analysis.read_text(encoding="utf-8")))
sections = ["AIUsageTracker third-party notices\n\n"
            "The portable Windows package includes the following open-source software.\n"
            "Each copyright and license text below is reproduced from its installed distribution.\n"
            "PyInstaller's bootloader is covered by its stated distribution exception.\n"]
for name in sorted(names):
    distribution = metadata.distribution(name)
    files = [file for file in distribution.files or []
             if re.search(r"^(license|licence|copying|notice)([.\-]|$)", file.name, re.I)]
    if not files and name.startswith("winrt-"):
        sections.append(f"\n{'=' * 72}\n{name} {distribution.version}\n" +
                        (ROOT / "assets/licenses/pywinrt-LICENSE.txt").read_text(encoding="utf-8"))
        continue
    if not files:
        raise RuntimeError(f"License text missing for {name}")
    sections.append(f"\n{'=' * 72}\n{name} {distribution.version}\n")
    for file in files:
        sections.append(f"\n{file.name}\n\n" + distribution.locate_file(file).read_text(encoding="utf-8", errors="replace"))

base = Path(sys.base_prefix)
for label, file in [("Python", base / "LICENSE.txt"),
                    ("Tcl", ROOT / "assets/licenses/tcl-LICENSE.txt"),
                    ("Tk", base / "tcl/tk8.6/license.terms")]:
    sections.append(f"\n{'=' * 72}\n{label}\n\n" + file.read_text(encoding="utf-8"))
(ROOT / "THIRD-PARTY-NOTICES.txt").write_text("\n".join(sections), encoding="utf-8")
print(f"Collected notices for {len(names)} distributions plus Python and Tcl/Tk.")
