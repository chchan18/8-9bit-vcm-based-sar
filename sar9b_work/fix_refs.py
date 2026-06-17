"""
Fix TB references in-place using schHiReplace.
Avoid delete+create since schCreateInst is unreliable through the bridge.
"""
from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
SRC = "8BIT400MVcmredundancySAR"
DST = "SAR9B_400MV"

# 1. First copy VA cells on disk and refresh lib
print("1. Refreshing library...")
# Read cdsinfo.tag to force library re-index
c.execute_skill(f'''
  let((lib)
    lib = ddGetObj("{DST}")
    lib~>refresh
    t)
''', timeout=10)

# Check again
for cell in ["decode_redun9to8", "DAC8b_va"]:
    r = c.execute_skill(f'''
      let((cv)
        cv = ddGetObj("{DST}" "{cell}")
        when(cv "FOUND" "NOT_FOUND"))
    ''', timeout=10)
    print(f"  {cell}: {r.output}")

# 2. Delete and re-copy TB
print("\n2. Fresh TB copy...")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "a")
    when(cv dbDelete(cv) "DEL" "NF"))
''', timeout=15)
print(f"  Delete: {r.output}")

r = c.execute_skill(f'''
  let((src dst)
    src = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "r")
    dst = dbCopyCellView(src "{DST}" "ADC_9B_tb" "schematic" "" t)
    dbClose(src) dbClose(dst) "OK")
''', timeout=15)
print(f"  Copy: {r.output}")

# 3. Use schHiReplace to fix library references IN-PLACE
# Key insight: use schHiReplace on libName, not delete+create
print("\n3. Fixing I0 lib/cell reference...")
r = c.execute_skill(f'''
  let((cv count)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "a")
    count = schHiReplace(?replaceAll t ?propName "libName" ?condOp "equal"
              ?propValue "{SRC}" ?newPropName "libName" ?newPropValue "{DST}")
    count = schHiReplace(?replaceAll t ?propName "cellName" ?condOp "equal"
              ?propValue "TOP_redun1_ADC" ?newPropName "cellName" ?newPropValue "TOP_9B_ADC")
    dbSave(cv)
    dbClose(cv)
    count)
''', timeout=15)
print(f"  I0 fix: {r.output}")

# 4. Fix I15 lib reference
print("\n4. Fixing I15 lib reference...")
r = c.execute_skill(f'''
  let((cv count)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "a")
    count = schHiReplace(?replaceAll t ?propName "libName" ?condOp "equal"
              ?propValue "{SRC}" ?newPropName "libName" ?newPropValue "{DST}")
    dbSave(cv)
    dbClose(cv)
    count)
''', timeout=15)
print(f"  I15 fix: {r.output}")

# 5. Fix I14 (decode) lib reference
print("\n5. Fixing I14 lib reference...")
r = c.execute_skill(f'''
  let((cv count)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "a")
    count = schHiReplace(?replaceAll t ?propName "libName" ?condOp "equal"
              ?propValue "{SRC}" ?newPropName "libName" ?newPropValue "{DST}")
    dbSave(cv)
    dbClose(cv)
    count)
''', timeout=15)
print(f"  I14 fix: {r.output}")

# 6. Final verification
print("\n6. Final TB state:")
r = c.execute_skill(f'''
  let((cv result)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "r")
    result = nil
    when(cv
      foreach(inst cv~>instances
        result = cons(strcat(inst~>name "|" inst~>libName "|" inst~>cellName) result))
      dbClose(cv))
    result)
''', timeout=10)
if r.output:
    for item in r.output.replace("(","").replace(")","").replace('"',"").split():
        item = item.strip()
        if item and '|' in item:
            parts = item.split('|')
            lib_ok = parts[1] in [DST, "analogLib", "basic"]
            cell = parts[2]
            flag = "OK" if lib_ok else "FIX!"
            print(f"  [{flag}] {parts[0]:5s} | {parts[1]} | {cell}")
