#!/usr/bin/env python3
"""Create missing SAR9B CDF params for the Verilog-A stop cells."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


SRC_LIB = "8BIT400MVcmredundancySAR"
LIB = "SAR9B_400MV"
TB_CELL = "ADC_9B_tb_best_q4"

PARAMS = {
    "DAC8b_va": {
        "N": "8",
        "VFS": "0.9",
        "VTH": "0.45",
        "trise": "1e-09",
        "tfall": "1e-09",
        "td": "0",
        "rout": "1",
    },
    "decode_redun9to8": {
        "vth": "0.45",
        "vlogic": "0.9",
        "trise": "1e-11",
        "tfall": "1e-11",
        "tdelay": "0",
    },
}


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
    for cell, params in PARAMS.items():
        param_forms = "\n".join(
            f'''
  unless(cdfFindParamByName(cdf "{name}")
    cdfCreateParam(
      cdf
      ?name "{name}"
      ?prompt "{name}"
      ?defValue "{default}"
      ?type "string"
      ?parseAsNumber "yes"
      ?parseAsCEL "yes"
      ?display "artParameterInToolDisplay('{name})"))'''
            for name, default in params.items()
        )
        run_skill(
            client,
            f"create CDF params and viewInfo {LIB}/{cell}",
            f'''
let((srcCell dstCell srcCdf cdf names)
  srcCell = ddGetObj("{SRC_LIB}" "{cell}")
  unless(srcCell error("missing source cell {SRC_LIB}/{cell}"))
  srcCdf = cdfGetBaseCellCDF(srcCell)
  unless(srcCdf error("missing source CDF {SRC_LIB}/{cell}"))
  dstCell = ddGetObj("{LIB}" "{cell}")
  unless(dstCell error("missing cell {LIB}/{cell}"))
  cdf = cdfGetBaseCellCDF(dstCell)
  unless(cdf cdf = cdfCreateBaseCellCDF(dstCell))
  unless(cdf error("could not create CDF for {LIB}/{cell}"))
{param_forms}
  cdf~>propList = srcCdf~>propList
  cdfSaveCDF(cdf)
  names = list("params" cdf~>parameters~>name "propList" cdf~>propList)
  names)
''',
            timeout=60,
        )

    run_skill(
        client,
        f"update CDF inst params in {LIB}/{TB_CELL}",
        f'''
let((cv i14 i15 out)
  cv = dbOpenCellViewByType("{LIB}" "{TB_CELL}" "schematic" "" "a")
  unless(cv error("cannot open TB"))
  i14 = dbGetInstByName(cv "I14")
  i15 = dbGetInstByName(cv "I15")
  unless(i14 && i15 error("missing I14/I15"))
  cdfUpdateInstParam(i14)
  cdfUpdateInstParam(i15)
  out = list(
    "I14" length(i14~>instTerms) i14~>instTerms~>name i14~>prop~>name i14~>prop~>value
    "I15" length(i15~>instTerms) i15~>instTerms~>name i15~>prop~>name i15~>prop~>value)
  schCheck(cv)
  dbSave(cv)
  dbClose(cv)
  out)
''',
        timeout=120,
    )


if __name__ == "__main__":
    main()
