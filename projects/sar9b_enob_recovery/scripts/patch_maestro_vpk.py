#!/usr/bin/env python3
"""Patch a SAR9B Maestro setup copy so all Vpk entries use one value."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


DEFAULT_SOURCE = Path(
    "sar9b_work/iterations/sar9b_maestro_best_q4/maestro_files_loaded_phase_p2200"
)
DEFAULT_DEST = Path(
    "projects/sar9b_enob_recovery/artifacts/maestro_files_vpk800_p2200"
)


def patch_active_state(text: str, value: str) -> tuple[str, int]:
    pattern = re.compile(
        r'(<field Name="name" Type="string">"Vpk"</field>\s*'
        r'<field Name="expression" Type="string">")([^"]+)("</field>)',
        re.MULTILINE,
    )
    return pattern.subn(rf"\g<1>{value}\g<3>", text)


def patch_sdb(text: str, value: str) -> tuple[str, int]:
    pattern = re.compile(
        r"(<var>Vpk\s*<value>)([^<]+)(</value>)",
        re.MULTILINE,
    )
    return pattern.subn(rf"\g<1>{value}\g<3>", text)


def count_vpk_values(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for match in re.finditer(
        r'(?:<var>Vpk\s*<value>|<field Name="name" Type="string">"Vpk"</field>\s*'
        r'<field Name="expression" Type="string">"?)([^<"]+)',
        text,
        re.MULTILINE,
    ):
        values[match.group(1)] = values.get(match.group(1), 0) + 1
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--value", default="800m")
    args = parser.parse_args()

    source = args.source.resolve()
    dest = args.dest.resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    manifest = {
        "source": str(source),
        "dest": str(dest),
        "target_vpk": args.value,
        "files": {},
    }

    for filename in ["active.state", "maestro.sdb"]:
        src = source / filename
        dst = dest / filename
        text = src.read_text(encoding="utf-8", errors="replace")
        before = count_vpk_values(text)
        if filename == "active.state":
            patched, replacements = patch_active_state(text, args.value)
        else:
            patched, replacements = patch_sdb(text, args.value)
        after = count_vpk_values(patched)
        dst.write_text(patched, encoding="utf-8")
        manifest["files"][filename] = {
            "before_vpk_values": before,
            "after_vpk_values": after,
            "replacements": replacements,
        }

    manifest_path = dest / "patch_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved patched Maestro setup: {dest}", flush=True)


if __name__ == "__main__":
    main()
