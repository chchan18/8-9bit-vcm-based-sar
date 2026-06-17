from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
SRC = "8BIT400MVcmredundancySAR"
DST = "SAR9B_400MV"

# First, refresh DD cache to pick up disk-copied cells
print("1. Checking VA cells visible in DST...")
for cell in ["decode_redun9to8", "DAC8b_va"]:
    r = c.execute_skill(f'''
      let((cv)
        cv = ddGetObj("{DST}" "{cell}")
        when(cv
          let((vlist)
            vlist = nil
            foreach(v cv~>views vlist = cons(v~>name vlist))
            vlist)
          "NOT_FOUND"))
    ''', timeout=10)
    print(f"  {cell}: {r.output}")

# 2. Delete and re-copy TB
print("\n2. Re-copying TB (with VA cells now available)...")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "a")
    when(cv dbDelete(cv) "DELETED" "NOT_FOUND"))
''', timeout=15)
print(f"  Delete: {r.output}")

r = c.execute_skill(f'''
  let((src dst)
    src = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "r")
    dst = dbCopyCellView(src "{DST}" "ADC_9B_tb" "schematic" "" t)
    dbClose(src)
    dbClose(dst)
    "COPIED")
''', timeout=15)
print(f"  Copy: {r.output}")

# 3. Check resulting instances
print("\n3. TB instances after copy:")
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
            print(f"  {parts[0]:5s} {parts[1]} / {parts[2]}")

# 4. Fix I0: switch from SRC/TOP_redun1_ADC to DST/TOP_9B_ADC
print("\n4. Fixing I0...")
r = c.execute_skill(f'''
  let((cv inst xy orient)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "a")
    inst = dbGetInstByName(cv "I0")
    when(inst
      xy = inst~>xy
      orient = inst~>orient
      ; Delete old
      schDelete(inst)
      ; Create new with correct lib/cell
      schCreateInst(cv "{DST}" "TOP_9B_ADC" "symbol" xy orient "I0")
      dbSave(cv)
      "SWITCHED"
      "NO_I0_FOUND")
    dbClose(cv))
''', timeout=15)
print(f"  {r.output}")

# 5. Fix I15: switch from SRC/DAC8b_va to DST/DAC8b_va
print("\n5. Fixing I15 (DAC)...")
r = c.execute_skill(f'''
  let((cv inst xy orient)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "a")
    inst = dbGetInstByName(cv "I15")
    when(inst
      xy = inst~>xy
      orient = inst~>orient
      schDelete(inst)
      schCreateInst(cv "{DST}" "DAC8b_va" "symbol" xy orient "I15")
      dbSave(cv)
      "SWITCHED"
      "NO_I15_FOUND")
    dbClose(cv))
''', timeout=15)
print(f"  {r.output}")

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
            flag = "OK" if parts[1] == DST else "FIX_NEEDED"
            print(f"  [{flag}] {parts[0]:5s} {parts[1]} / {parts[2]}")

print("\n=== DONE ===")
