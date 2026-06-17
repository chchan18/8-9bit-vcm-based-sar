#!/usr/bin/env python3
"""Inspect CDF/simInfo for SAR9B Verilog-A stop cells."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


SRC_LIB = "8BIT400MVcmredundancySAR"
LIB = "SAR9B_400MV"
CELLS = ["DAC8b_va", "decode_redun9to8"]


def skill_ok(result) -> bool:
    return bool(getattr(result, "status", None) and result.status.value == "success")


def run_skill(client: VirtuosoClient, title: str, code: str, timeout: int = 30) -> str:
    print(f"\n== {title} ==")
    result = client.execute_skill(code, timeout=timeout)
    print(f"status={result.status.value}")
    print(f"output={result.output}")
    if result.errors:
        print(f"errors={result.errors}")
    if not skill_ok(result):
        raise RuntimeError(f"{title} failed")
    return result.output or ""


def main() -> None:
    client = VirtuosoClient.from_env()
    for lib in [SRC_LIB, LIB]:
        for cell in CELLS:
            run_skill(
                client,
                f"inspect CDF {lib}/{cell}",
                f'''
let((cellObj cdf sim out)
  cellObj = ddGetObj("{lib}" "{cell}")
  cdf = when(cellObj cdfGetBaseCellCDF(cellObj))
  sim = when(cdf get(cdf~>simInfo 'spectre))
  out = list(
    "has_cdf" if(cdf t nil)
    "param_names" if(cdf cdf~>parameters~>name nil)
    "param_prompts" if(cdf cdf~>parameters~>prompt nil)
    "param_details" if(cdf
      foreach(mapcar p cdf~>parameters
        list(
          p~>name p~>prompt p~>defValue p~>valueType p~>parseAsNumber
          p~>parseAsCEL p~>display p~>editable p~>storeDefault))
      nil)
    "simInfo" if(sim t nil)
    "componentName" if(sim sim~>componentName nil)
    "termOrder" if(sim sim~>termOrder nil)
    "termMapping" if(sim sim~>termMapping nil)
    "instParameters" if(sim sim~>instParameters nil)
    "otherParameters" if(sim sim~>otherParameters nil)
    "propMapping" if(sim sim~>propMapping nil)
    "modelName" if(sim sim~>modelName nil))
  out)
''',
                timeout=60,
            )


if __name__ == "__main__":
    main()
