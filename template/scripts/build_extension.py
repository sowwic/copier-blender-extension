#!/usr/bin/env python3
"""Build the Blender extension zip.

Blender installs an extension without fetching anything, so the zip carries the wheels
of this package and of its dependencies (the locked ones, `uv export`). The
dependencies must be pure Python: a zip with platform specific wheels needs one build
per platform.

    BLENDER=/path/to/Blender python scripts/build_extension.py [--output-dir dist]
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXTENSION_DIR = ROOT / "extension"
BUILD_DIR = ROOT / "build"
WHEELS_MARKER = "# The wheels are added by `scripts/build_extension.py`."


def run(*command: str | os.PathLike, cwd: pathlib.Path | None = None) -> None:
    """Run a command, stopping the build when it fails."""
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def build_dependency_wheels(wheels_dir: pathlib.Path) -> None:
    """Put a wheel of every locked dependency of the project into a folder.

    Args:
        wheels_dir (pathlib.Path): folder to put the wheels in.
    """
    requirements = BUILD_DIR / "requirements.txt"
    exported = subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-hashes",
            "--format",
            "requirements-txt",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    lines = [line for line in exported.splitlines() if line and not line.startswith("#")]
    if not lines:
        return
    requirements.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run("uvx", "pip", "wheel", "--no-deps", "-r", requirements, "-w", wheels_dir)


def write_manifest(source_dir: pathlib.Path, wheel_names: list[str]) -> None:
    """Put the wheels into the manifest of the extension being built.

    Args:
        source_dir (pathlib.Path): folder of the extension, holds the manifest.
        wheel_names (list[str]): file names of the wheels in its `wheels` folder.
    """
    manifest = source_dir / "blender_manifest.toml"
    text = manifest.read_text(encoding="utf-8")
    version = tomllib.loads(text)["version"]
    expected = (ROOT / "VERSION").read_text().strip()
    if version != expected:
        raise SystemExit(
            f"blender_manifest.toml is at version {version}, VERSION says {expected}"
        )
    if WHEELS_MARKER not in text:
        raise SystemExit("blender_manifest.toml lost the line marking where wheels go")
    wheels = ",\n".join(f'  "./wheels/{name}"' for name in wheel_names)
    manifest.write_text(
        text.replace(WHEELS_MARKER, f"wheels = [\n{wheels},\n]"), encoding="utf-8"
    )


def main() -> None:
    """Assemble the extension and let Blender build the zip."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--blender", default=os.environ.get("BLENDER"))
    parser.add_argument("--output-dir", type=pathlib.Path, default=ROOT / "dist")
    args = parser.parse_args()
    if not args.blender:
        raise SystemExit("Set BLENDER to the Blender executable, or pass --blender")

    BUILD_DIR.mkdir(exist_ok=True)
    source_dir = BUILD_DIR / "extension"
    shutil.rmtree(source_dir, ignore_errors=True)
    shutil.copytree(
        EXTENSION_DIR, source_dir, ignore=shutil.ignore_patterns("__pycache__", "wheels")
    )
    wheels_dir = source_dir / "wheels"
    wheels_dir.mkdir()

    run("uv", "build", "--wheel", "--out-dir", wheels_dir, ROOT)
    build_dependency_wheels(wheels_dir)
    write_manifest(source_dir, sorted(path.name for path in wheels_dir.glob("*.whl")))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    run(
        args.blender,
        "--command",
        "extension",
        "build",
        "--source-dir",
        source_dir,
        "--output-dir",
        args.output_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
