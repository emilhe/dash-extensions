from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
PACKAGE_JSON = ROOT / "package.json"
PYPROJECT = ROOT / "pyproject.toml"

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
HEADING_RE = re.compile(r"^## \[(?P<version>[^\]]+)\](?: - (?P<date>.*))?$")


def normalize_version(version: str) -> str:
    version = version.strip()
    if version.startswith("v"):
        version = version[1:]
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"Version must be semantic (x.y.z), got: {version}")
    return version


def read_package() -> dict:
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))


def write_package(data: dict) -> None:
    PACKAGE_JSON.write_text(f"{json.dumps(data, indent=2)}\n", encoding="utf-8")


def read_pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def sync_pyproject_from_package(package: dict) -> None:
    version = package["version"]
    description = package.get("description", "")
    content = PYPROJECT.read_text(encoding="utf-8")
    content = re.sub(r'^version = ".*"$', f'version = "{version}"', content, count=1, flags=re.MULTILINE)
    content = re.sub(r'^description = ".*"$', f'description = "{description}"', content, count=1, flags=re.MULTILINE)
    PYPROJECT.write_text(content, encoding="utf-8")


def find_changelog_section(lines: list[str], version: str) -> tuple[int, int] | None:
    starts: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            starts.append((match.group("version"), i))
    for idx, (v, start) in enumerate(starts):
        if v != version:
            continue
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(lines)
        return start, end
    return None


def ensure_changelog_section(version: str) -> bool:
    lines = CHANGELOG.read_text(encoding="utf-8").splitlines()
    if find_changelog_section(lines, version) is not None:
        return False

    today = dt.datetime.now().strftime("%d-%m-%y")
    insert_at = next((i for i, line in enumerate(lines) if HEADING_RE.match(line)), len(lines))
    section = [
        f"## [{version}] - {today}",
        "",
        "### Changed",
        "",
        "-   TODO",
        "",
    ]

    if insert_at > 0 and lines[insert_at - 1].strip() != "":
        section.insert(0, "")

    updated = lines[:insert_at] + section + lines[insert_at:]
    CHANGELOG.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return True


def get_changelog_section(version: str) -> str:
    lines = CHANGELOG.read_text(encoding="utf-8").splitlines()
    section = find_changelog_section(lines, version)
    if section is None:
        raise ValueError(f"Could not find CHANGELOG section for version {version}")
    start, end = section
    body = "\n".join(lines[start:end]).strip()
    if not body:
        raise ValueError(f"Changelog section for {version} is empty")
    return body + "\n"


def prepare(version: str) -> None:
    package = read_package()
    package["version"] = version
    write_package(package)

    sync_pyproject_from_package(package)

    created = ensure_changelog_section(version)
    if created:
        print(f"Inserted CHANGELOG template for {version}")
    print(f"Prepared release files for {version}")


def verify(version: str) -> None:
    package = read_package()
    pyproject = read_pyproject()

    package_version = package.get("version")
    pyproject_version = pyproject.get("project", {}).get("version")
    if package_version != version:
        raise ValueError(f"package.json has {package_version}, expected {version}")
    if pyproject_version != version:
        raise ValueError(f"pyproject.toml has {pyproject_version}, expected {version}")

    section = get_changelog_section(version)
    if "TODO" in section:
        raise ValueError(f"CHANGELOG section for {version} still contains TODO")

    print(f"Verified release metadata for {version}")


def release_notes(version: str, output: Path | None) -> None:
    notes = get_changelog_section(version)
    if output is None:
        print(notes, end="")
        return
    output.write_text(notes, encoding="utf-8")
    print(f"Wrote release notes to {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Release helpers for dash-extensions")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_prepare = subparsers.add_parser("prepare", help="Sync versions and ensure changelog section exists")
    p_prepare.add_argument("--version", required=True)

    p_verify = subparsers.add_parser("verify", help="Validate versions and changelog section")
    p_verify.add_argument("--version", required=True)

    p_notes = subparsers.add_parser("release-notes", help="Extract changelog section for a version")
    p_notes.add_argument("--version", required=True)
    p_notes.add_argument("--output", type=Path)

    args = parser.parse_args()
    try:
        version = normalize_version(args.version)
        if args.cmd == "prepare":
            prepare(version)
        elif args.cmd == "verify":
            verify(version)
        elif args.cmd == "release-notes":
            release_notes(version, args.output)
        else:  # pragma: no cover
            raise ValueError(f"Unsupported command: {args.cmd}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
