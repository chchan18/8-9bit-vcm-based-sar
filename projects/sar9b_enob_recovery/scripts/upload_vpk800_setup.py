#!/usr/bin/env python3
"""Upload the patched Vpk=800m Maestro setup after backing up the remote setup."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LOCAL_SETUP = Path(
    "projects/sar9b_enob_recovery/artifacts/maestro_files_vpk800_p2200"
)
REMOTE_MAESTRO = (
    "/home/IC/Desktop/Project/SAR9B_400MV/ADC_9B_tb_best_q4/maestro"
)
BACKUP_ROOT = Path("projects/sar9b_enob_recovery/artifacts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-dir", type=Path, default=LOCAL_SETUP)
    parser.add_argument("--apply", action="store_true", help="Actually upload files")
    args = parser.parse_args()

    setup_dir = args.setup_dir.resolve()
    for filename in ["active.state", "maestro.sdb"]:
        if not (setup_dir / filename).exists():
            raise FileNotFoundError(setup_dir / filename)

    client = VirtuosoClient.from_env()
    backup_dir = BACKUP_ROOT / f"remote_backup_before_vpk800_{int(time.time())}"
    manifest = {
        "remote_maestro": REMOTE_MAESTRO,
        "setup_dir": str(setup_dir),
        "backup_dir": str(backup_dir),
        "applied": bool(args.apply),
        "files": ["active.state", "maestro.sdb"],
    }

    if args.apply:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for filename in manifest["files"]:
            client.download_file(
                f"{REMOTE_MAESTRO}/{filename}",
                str(backup_dir / filename),
            )
        for filename in manifest["files"]:
            client.upload_file(
                str(setup_dir / filename),
                f"{REMOTE_MAESTRO}/{filename}",
            )
    else:
        print("Dry run only. Re-run with --apply to upload.", flush=True)

    manifest_path = setup_dir / "upload_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
