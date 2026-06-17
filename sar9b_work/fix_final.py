from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"

# Step 1: Copy symbol from TOP_redun1_ADC to TOP_9B_BINARY
print("1. Copying symbol view...")
r = c.execute_skill(f'''
  let((src_sym dst_sym)
    src_sym = dbOpenCellViewByType("{LIB}" "TOP_redun1_ADC" "symbol" "" "r")
    dst_sym = dbCopyCellView(src_sym "{LIB}" "TOP_9B_BINARY" "symbol" "" t)
    dbClose(src_sym)
    dbClose(dst_sym)
    "SYMBOL_COPIED")
''', timeout=15)
print(f"   {r.output}")

# Verify
r = c.execute_skill(f'ddGetObj("{LIB}" "TOP_9B_BINARY")~>views~>name', timeout=10)
print(f"   Views: {r.output}")

# Step 2: Re-create ADC_9B_tb_v3 from scratch
TB = "ADC_9B_tb_v3"

# Delete old
print(f"\n2. Deleting old {TB}...")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    when(cv dbDelete(cv) "DELETED")
    "OK")
''', timeout=15)
print(f"   {r.output}")

# Copy fresh
print(f"\n3. Copying ADC_redun1_tb -> {TB}...")
r = c.execute_skill(f'''
  let((src dst)
    src = dbOpenCellViewByType("{LIB}" "ADC_redun1_tb" "schematic" "" "r")
    dst = dbCopyCellView(src "{LIB}" "{TB}" "schematic" "" t)
    dbClose(src)
    dbClose(dst)
    "COPIED")
''', timeout=15)
print(f"   {r.output}")

# Step 4: Delete old I0, create new I0 with TOP_9B_BINARY symbol
print(f"\n4. Replacing I0...")
r = c.execute_skill(f'''
  let((cv old_inst new_inst xy orient)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "a")
    old_inst = dbGetInstByName(cv "I0")
    xy = old_inst~>xy
    orient = old_inst~>orient
    schDelete(old_inst)
    new_inst = schCreateInst(cv "{LIB}" "TOP_9B_BINARY" "symbol" xy orient "I0")
    dbSave(cv)
    dbClose(cv)
    new_inst~>cellName)
''', timeout=15)
print(f"   New I0: {r.output}")

# Step 5: Verify
print(f"\n5. Verification...")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "{TB}" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    dbClose(cv)
    list(inst~>cellName inst~>libName))
''', timeout=10)
print(f"   I0: {r.output}")

# List all
print(f"\n6. All instances:")
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
    for item in r.output.replace("(","").replace(")","").replace('"',"").split():
        if item.strip() and ':' in item:
            print(f"   {item.strip()}")

print("\n=== TB CHECK COMPLETE ===")
