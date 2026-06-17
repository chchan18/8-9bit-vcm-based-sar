#!/usr/bin/env python3
"""Inspect relevant SAR9B_400MV cells and references."""

from virtuoso_bridge import VirtuosoClient


CELLS = [
    "TOP_redun1_ADC",
    "TOP_9B_ADC",
    "TOP_9B_BINARY",
    "ADC_redun1_tb",
    "ADC_9B_tb",
    "DAC8b_va",
    "DAC9b_va",
    "decode_redun9to8",
]


def main():
    client = VirtuosoClient.from_env()
    for cell in CELLS:
        r = client.execute_skill(
            f'''
let((obj views)
  obj = ddGetObj("SAR9B_400MV" "{cell}")
  views = if(obj obj~>views~>name nil)
  views)
''',
            timeout=20,
        )
        print(f"SAR9B_400MV/{cell}: {r.output}")
    r = client.execute_skill(
        '''
let((obj cells)
  obj = ddGetObj("SAR9B_400MV")
  cells = nil
  when(obj
    foreach(c obj~>cells
      cells = cons(c~>name cells)))
  cells)
''',
        timeout=20,
    )
    print(f"\nAll SAR9B_400MV cells:\n{r.output}")


if __name__ == "__main__":
    main()
