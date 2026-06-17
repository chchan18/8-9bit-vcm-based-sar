#!/usr/bin/env python3
"""Create a tiny schematic to verify schematic editing works in this session."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_label_instance_term as label_term,
)


LIB = "SAR9B_400MV"
CELL = "TB_SUBMOD_SMOKE_RC"


def main() -> None:
    client = VirtuosoClient.from_env()
    with client.schematic.edit(LIB, CELL) as sch:
        sch.add(inst("analogLib", "vdc", "symbol", "V0", 0.0, 0.0, "R0"))
        sch.add(inst("analogLib", "res", "symbol", "R0", 2.0, 0.0, "R0"))
        sch.add(inst("analogLib", "cap", "symbol", "C0", 4.0, 0.0, "R0"))
        sch.add(inst("analogLib", "gnd", "symbol", "G0", 0.0, -2.0, "R0"))
        sch.add(label_term("V0", "PLUS", "VDD"))
        sch.add(label_term("V0", "MINUS", "0"))
        sch.add(label_term("G0", "gnd!", "0"))
        sch.add(label_term("R0", "PLUS", "VDD"))
        sch.add(label_term("R0", "MINUS", "OUT"))
        sch.add(label_term("C0", "PLUS", "OUT"))
        sch.add(label_term("C0", "MINUS", "0"))
    print(f"Created {LIB}/{CELL}/schematic", flush=True)


if __name__ == "__main__":
    main()
