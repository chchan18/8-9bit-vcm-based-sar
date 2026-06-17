#!/usr/bin/env python3
"""Compare schematic extraction metadata for known-good and new testbenches."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


TARGETS = [
    ("SAR9B_400MV", "ADC_9B_tb_best_q4"),
    ("SAR9B_400MV", "TB_SUBMOD_COMPARATOR_PERF"),
    ("SAR9B_400MV", "TB_SUBMOD_CLK_NOOVERLAP_PERF"),
    ("SAR9B_400MV", "TB_SUBMOD_ASYCTRL_9CLK_PERF"),
    ("SAR9B_400MV", "TB_SUBMOD_BOOTSTRAP_DIFF_PERF"),
    ("8BIT400MVcmredundancySAR", "ADC_redun1_tb"),
]


def main() -> None:
    client = VirtuosoClient.from_env()
    for lib, cell in TARGETS:
        result = client.execute_skill(
            f'''
let((cv out)
  cv = dbOpenCellViewByType("{lib}" "{cell}" "schematic" "" "r")
  unless(cv error("open failed"))
  out = list(
    "lib" "{lib}"
    "cell" "{cell}"
    "propNames" cv~>prop~>name
    "propValues" cv~>prop~>value
    "connectivityLastUpdated" cv~>connectivityLastUpdated
    "lastSchematicExtraction" cv~>lastSchematicExtraction
    "schGeometryLastUpdated" cv~>schGeometryLastUpdated
    "schXtrVersion" cv~>schXtrVersion
    "modified" cv~>modified)
  dbClose(cv)
  out)
''',
            timeout=60,
        )
        print(f"--- {lib}/{cell}: {result.status.value}", flush=True)
        print(result.output or "", flush=True)
        if result.errors:
            print(result.errors, flush=True)


if __name__ == "__main__":
    main()
