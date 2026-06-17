#!/usr/bin/env python3
"""Inspect available 9-bit cells and Maestro setups."""

from virtuoso_bridge import VirtuosoClient


CHECKS = [
    ("8BIT400MVcmredundancySAR", "TOP_9B_BINARY"),
    ("8BIT400MVcmredundancySAR", "ADC_9B_tb"),
    ("8BIT400MVcmredundancySAR", "ADC_9B_tb_v2"),
    ("8BIT400MVcmredundancySAR", "ADC_9B_tb_v3"),
    ("SAR9B_400MV", "TOP_9B_ADC"),
    ("SAR9B_400MV", "ADC_9B_tb"),
]


def main():
    client = VirtuosoClient.from_env()
    for lib, cell in CHECKS:
        print(f"\n== {lib}/{cell} ==")
        r = client.execute_skill(
            f'''
let((obj views setups insts)
  obj = ddGetObj("{lib}" "{cell}")
  views = if(obj obj~>views~>name nil)
  setups = errset(maeGetSetupNames("{lib}" "{cell}" "maestro") nil)
  insts = nil
  when(member("schematic" views)
    let((cv)
      cv = dbOpenCellViewByType("{lib}" "{cell}" "schematic" "" "r")
      when(cv
        foreach(inst cv~>instances
          insts = cons(strcat(inst~>name ":" inst~>libName "/" inst~>cellName "/" inst~>viewName) insts))
        dbClose(cv))))
  list(views setups insts))
''',
            timeout=30,
        )
        print(f"status={r.status.value}")
        print(f"output={r.output}")
        if r.errors:
            print(f"errors={r.errors}")


if __name__ == "__main__":
    main()
