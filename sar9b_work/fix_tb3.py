from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"
TB = "ADC_9B_tb_v3"

# Direct: check then fix
print("Step 1: Read I0 cellName directly...")
r = c.execute_skill(f'''
  let((cv inst cellName)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    cellName = inst~>cellName
    dbClose(cv)
    cellName)
''', timeout=10)
print(f"  Current I0 cellName: [{r.output}]")

# Fix via inst~>master
print("\nStep 2: Fix via master change...")
r = c.execute_skill(f'''
  let((cv inst newM)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    inst = dbGetInstByName(cv "I0")
    newM = dbOpenCellViewByType("{LIB}" "TOP_9B_BINARY" "symbol")
    inst~>master = newM
    dbSave(cv)
    dbClose(cv)
    dbClose(newM)
    "DONE")
''', timeout=15)
print(f"  Fix: {r.output}")

# Re-read
print("\nStep 3: Re-read I0...")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    dbClose(cv)
    inst~>cellName)
''', timeout=10)
print(f"  New I0 cellName: [{r.output}]")
