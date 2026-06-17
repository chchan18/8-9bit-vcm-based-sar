from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"
TB = "ADC_9B_tb_v3"

# Check if symbol exists and is valid
print("1. Check TOP_9B_BINARY symbol...")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{LIB}" "TOP_9B_BINARY" "symbol" "" "r")
    list(cv~>cellName cv~>viewName cv~>terminals~>name))
''', timeout=10)
print(f"   Symbol: {r.output}")

# Check TB
print("\n2. TB instances count...")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    list(length(cv~>instances)))
''', timeout=10)
print(f"   Instance count: {r.output}")

# Try creating I0 with different approach
print("\n3. Create I0 (try 2)...")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    inst = schCreateInst(cv "{LIB}" "TOP_9B_BINARY" "symbol" list(-3.25 0.6875) "R0" "I0_NEW")
    when(inst
      dbSave(cv)
      list("CREATED" inst~>cellName))
    dbClose(cv)
    "DONE")
''', timeout=15)
print(f"   {r.output}")

# Check if I0_NEW was created
print("\n4. Check I0_NEW...")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0_NEW")
    dbClose(cv)
    when(inst inst~>cellName "NOT_FOUND"))
''', timeout=10)
print(f"   {r.output}")

# Try with different library name - maybe the instance needs the same lib as the TB
print("\n5. Try explicit instance create via dbCreateInst...")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    inst = dbCreateInst(cv "{LIB}" "TOP_9B_BINARY" "symbol" "I0" list(-3.25 0.6875) "R0")
    when(inst
      dbSave(cv)
      list("DB_CREATED" inst~>cellName)
      list("DB_FAILED")))
    dbClose(cv)
    "DONE")
''', timeout=15)
print(f"   {r.output}")
