#!/usr/bin/env python3
"""Use a Spectre wrapper file so Maestro emits ahdl_include for SAR9B VA cells."""

from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import open_gui_session

from prepare_sar9b_maestro_best import LIB, OUT_DIR, TB_CELL
from start_sar9b_maestro_best_run import TEST_NAME


VA_FILES = [
    f"/home/IC/Desktop/Project/{LIB}/DAC9b_va/veriloga/veriloga.va",
]
REMOTE_WRAPPER = f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro/sar9b_va_ahdl.scs"
LOCAL_WRAPPER = OUT_DIR / "sar9b_va_ahdl.scs"


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 30) -> str:
    print(f"\n== {title} ==", flush=True)
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}", flush=True)
    print(f"output={result.output}", flush=True)
    if result.errors:
        print(f"errors={result.errors}", flush=True)
    if not skill_ok(result):
        raise RuntimeError(f"{title} failed")
    return result.output or ""


def ssh(client: VirtuosoClient, command: str, timeout: int = 30) -> str:
    if client.ssh_runner is None:
        raise RuntimeError("SSH runner is required")
    result = client.ssh_runner.run_command(command, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"remote command failed: {command}\n{result.stderr}")
    return result.stdout or ""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env()
    for path in VA_FILES:
        exists = ssh(client, f"test -f {path} && echo yes || echo no", timeout=20).strip()
        if exists != "yes":
            raise RuntimeError(f"missing remote Verilog-A file: {path}")

    wrapper_text = "\n".join(
        [
            "// Generated SAR9B Verilog-A AHDL include wrapper.",
            "simulator lang=spectre",
            *[f'ahdl_include "{path}"' for path in VA_FILES],
            "",
        ]
    )
    LOCAL_WRAPPER.write_text(wrapper_text, encoding="utf-8")
    client.upload_file(str(LOCAL_WRAPPER), REMOTE_WRAPPER)
    remote_check = ssh(client, f"test -f {REMOTE_WRAPPER} && cat {REMOTE_WRAPPER}", timeout=20)

    session = open_gui_session(client, LIB, TB_CELL, timeout=90)
    before = run_skill(
        client,
        "read current definitionFiles",
        f'maeGetEnvOption("{TEST_NAME}" ?option "definitionFiles" ?session "{session}")',
        timeout=30,
    )
    run_skill(
        client,
        "set wrapper definitionFile",
        (
            f'maeSetEnvOption("{TEST_NAME}" ?options '
            f'`(("definitionFiles" ("{REMOTE_WRAPPER}")) '
            f'("allDefinitionFiles" ("{REMOTE_WRAPPER}"))) '
            f'?session "{session}")'
        ),
        timeout=60,
    )
    after = run_skill(
        client,
        "read updated definitionFiles",
        f'maeGetEnvOption("{TEST_NAME}" ?option "definitionFiles" ?session "{session}")',
        timeout=30,
    )
    run_skill(
        client,
        "save SAR9B Maestro setup",
        f'maeSaveSetup(?lib "{LIB}" ?cell "{TB_CELL}" ?view "maestro" ?session "{session}")',
        timeout=60,
    )

    remote_maestro = f"/home/IC/Desktop/Project/{LIB}/{TB_CELL}/maestro"
    grep = ssh(
        client,
        (
            "grep -R \"definitionFiles\\|allDefinitionFiles\\|sar9b_va_ahdl\\|DAC9b_va/veriloga\\|DAC8b_va/veriloga\\|decode_redun9to8/veriloga\" -n "
            f"{remote_maestro}/active.state {remote_maestro}/maestro.sdb {REMOTE_WRAPPER} || true"
        ),
        timeout=30,
    )
    local_dir = OUT_DIR / "maestro_files_after_ahdl_wrapper"
    local_dir.mkdir(parents=True, exist_ok=True)
    client.download_file(f"{remote_maestro}/active.state", str(local_dir / "active.state"))
    client.download_file(f"{remote_maestro}/maestro.sdb", str(local_dir / "maestro.sdb"))

    manifest = {
        "library": LIB,
        "testbench_cell": TB_CELL,
        "test_name": TEST_NAME,
        "session": session,
        "va_files": VA_FILES,
        "remote_wrapper": REMOTE_WRAPPER,
        "local_wrapper": str(LOCAL_WRAPPER),
        "remote_wrapper_contents": remote_check,
        "definition_files_before": before,
        "definition_files_after": after,
        "grep": grep,
    }
    out_path = OUT_DIR / "ahdl_wrapper_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
