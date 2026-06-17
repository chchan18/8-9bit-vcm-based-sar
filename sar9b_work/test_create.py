from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()

code = '''
  let((cv inst)
    cv = dbOpenCellViewByType("8BIT400MVcmredundancySAR" "ADC_9B_tb_v3" "schematic" "" "a")
    inst = dbCreateInst(cv "8BIT400MVcmredundancySAR" "TOP_9B_BINARY" "symbol" "I0_TEST" list(-3.25 0.6875) "R0")
    when(inst
      dbSave(cv)
      "CREATED"
      "FAILED")
    dbClose(cv))
'''
r = c.execute_skill(code, timeout=15)
print(f"dbCreateInst: status={r.status}, output={r.output}")
