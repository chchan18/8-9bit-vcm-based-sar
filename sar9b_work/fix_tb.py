from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"
TB = "ADC_9B_tb_v3"

# 1. Delete existing if any
print("1. Clean up...")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    when(cv
      dbDelete(cv)
      "DELETED")
    "OK")
''', timeout=15)
print(f"   {r.output}")

# 2. Fresh copy
print("\n2. Copying ADC_redun1_tb ->", TB)
r = c.execute_skill(f'''
  let((src dst)
    src = dbOpenCellViewByType("{LIB}" "ADC_redun1_tb" "schematic" "" "r")
    dst = dbCopyCellView(src "{LIB}" "{TB}" "schematic" "" t)
    dbClose(dst)
    dbClose(src)
    "COPIED")
''', timeout=15)
print(f"   {r.output}")

# 3. Switch I0 to TOP_9B_BINARY using schHiReplace
print("\n3. Switching I0 -> TOP_9B_BINARY...")
r = c.execute_skill(f'''
  let((cv result)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    result = schHiReplace(
      ?replaceAll t
      ?propName "cellName"
      ?condOp "equal"
      ?propValue "TOP_redun1_ADC"
      ?newPropName "cellName"
      ?newPropValue "TOP_9B_BINARY")
    dbSave(cv)
    dbClose(cv)
    ; return number of replacements
    list("REPLACED" result))
''', timeout=15)
print(f"   {r.output}")

# 4. Verify
print("\n4. Verification...")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    when(inst
      list(inst~>libName inst~>cellName inst~>viewName))
    dbClose(cv))
''', timeout=10)
print(f"   I0: {r.output}")

# 5. List instances
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
    for s in r.output.replace("(","").replace(")","").replace('"',"").split():
        if s.strip():
            print(f"   {s.strip()}")

print("\nDone. TB ready for Maestro.")
