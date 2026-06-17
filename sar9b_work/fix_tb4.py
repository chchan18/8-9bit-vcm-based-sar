from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"
TB = "ADC_9B_tb_v3"

# Read I0 position, orientation; delete; create new instance
print("1. Reading I0 properties...")
r = c.execute_skill(f'''
  let((cv inst xy orient)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    xy = inst~>xy
    orient = inst~>orient
    dbClose(cv)
    list(xy orient))
''', timeout=10)
print(f"   I0 xy+orient: {r.output}")

# Delete I0 and I14 (decode) -- we'll just leave I14 for now
print("\n2. Deleting I0...")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    inst = dbGetInstByName(cv "I0")
    schDelete(inst)
    dbSave(cv)
    dbClose(cv)
    "DELETED")
''', timeout=15)
print(f"   {r.output}")

# Create new I0 = TOP_9B_BINARY
print("\n3. Creating new I0 (TOP_9B_BINARY)...")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    inst = schCreateInst(cv "{LIB}" "TOP_9B_BINARY" "symbol" list(0 0) "R0" "I0")
    dbSave(cv)
    dbClose(cv)
    inst~>cellName)
''', timeout=15)
print(f"   New I0 cell: {r.output}")

# Verify
print("\n4. Verify...")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    dbClose(cv)
    inst~>cellName)
''', timeout=10)
print(f"   I0 cellName: {r.output}")

# List all instances
r = c.execute_skill(f'''
  let((cv result)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    result = nil
    foreach(inst cv~>instances
      result = cons(strcat(inst~>name ":" inst~>cellName) result))
    dbClose(cv)
    result)
''', timeout=10)
if r.output:
    # Parse SKILL list: ("a" "b" "c")
    raw = r.output.strip('()').replace('"','')
    items = [x.strip() for x in raw.split('" "') if x.strip()]
    if not items:
        items = [x.strip() for x in raw.split() if x.strip()]
    print("   Instances:")
    for item in sorted(items):
        if ':' in item:
            print(f"     {item}")
