from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"
TB = "ADC_9B_tb_v3"

print("Switching I0 via schReplaceInst...")
r = c.execute_skill(f'''
  let((cv inst newMaster)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    inst = dbGetInstByName(cv "I0")
    newMaster = dbOpenCellViewByType("{LIB}" "TOP_9B_BINARY" "symbol")
    when(inst && newMaster
      schReplaceInst(inst newMaster)
      dbSave(cv)
      list("REPLACED" inst~>cellName inst~>libName))
    dbClose(cv)
    dbClose(newMaster)
    "DONE")
''', timeout=15)
print(f"Result: {r.output}")

# Verify
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    when(inst
      list(inst~>libName inst~>cellName))
    dbClose(cv))
''', timeout=10)
print(f"I0: {r.output}")
