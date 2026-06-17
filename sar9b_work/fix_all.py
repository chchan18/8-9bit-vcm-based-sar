from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
SRC = "8BIT400MVcmredundancySAR"
DST = "SAR9B_400MV"

# 1. Check VA cells in DST
print("=== VA cells in DST ===")
for cell in ["decode_redun9to8", "DAC8b_va"]:
    r = c.execute_skill(f'''
      let((cv)
        cv = ddGetObj("{DST}" "{cell}")
        when(cv
          let((vlist)
            vlist = nil
            foreach(v cv~>views
              vlist = cons(v~>name vlist))
            vlist)
          "NOT_IN_{cell}"))
    ''', timeout=10)
    print(f"  {cell}: {r.output}")

# Delete existing DAC/decode in DST and re-copy
print("\n=== Force re-copy VA cells ===")
for cell in ["decode_redun9to8", "DAC8b_va"]:
    # Delete if exists
    r = c.execute_skill(f'''
      let((cv)
        cv = ddGetObj("{DST}" "{cell}")
        when(cv
          dbDelete(cv)
          "DELETED")
        "OK")
    ''', timeout=10)
    print(f"  Delete {cell}: {r.output}")

    # Copy all views
    r = c.execute_skill(f'''
      let((cv views)
        cv = ddGetObj("{SRC}" "{cell}")
        views = nil
        when(cv
          foreach(v cv~>views
            views = cons(v~>name views)))
        views)
    ''', timeout=10)
    if r.output:
        raw = r.output.replace("(","").replace(")","").replace('"',"").split()
        for view in [x.strip() for x in raw if x.strip()]:
            r2 = c.execute_skill(f'''
              let((src_v dst_v)
                src_v = dbOpenCellViewByType("{SRC}" "{cell}" "{view}" "" "r")
                when(src_v
                  dst_v = dbCopyCellView(src_v "{DST}" "{cell}" "{view}" "" t)
                  dbClose(src_v)
                  dbClose(dst_v)
                  "{view}_OK"
                  "{view}_FAIL"))
            ''', timeout=15)
            print(f"    {cell}/{view}: {r2.output}")

# 2. Create symbol for TOP_9B_ADC (copy from TOP_redun1_ADC)
print("\n=== Creating TOP_9B_ADC symbol ===")
r = c.execute_skill(f'''
  let((src_sym dst_sym)
    src_sym = dbOpenCellViewByType("{SRC}" "TOP_redun1_ADC" "symbol" "" "r")
    when(src_sym
      dst_sym = dbCopyCellView(src_sym "{DST}" "TOP_9B_ADC" "symbol" "" t)
      dbClose(src_sym)
      dbClose(dst_sym)
      "SYMBOL_OK"
      "NO_SRC_SYMBOL"))
''', timeout=15)
print(f"  {r.output}")

# 3. Verify TOP_9B_ADC views and caps
print("\n=== TOP_9B_ADC final check ===")
r = c.execute_skill(f'''
  let((cv vlist)
    cv = ddGetObj("{DST}" "TOP_9B_ADC")
    vlist = nil
    when(cv
      foreach(v cv~>views
        vlist = cons(v~>name vlist)))
    vlist)
''', timeout=10)
print(f"  Views: {r.output}")

r = c.execute_skill(f'''
  let((sch caps)
    sch = dbOpenCellViewByType("{DST}" "TOP_9B_ADC" "schematic" "" "r")
    caps = nil
    when(sch
      foreach(inst sch~>instances
        when(inst~>cellName == "cap"
          caps = cons(strcat(inst~>name "=" inst~>c) caps)))
      dbClose(sch))
    caps)
''', timeout=10)
if r.output:
    for item in r.output.replace("(","").replace(")","").replace('"',"").split():
        item = item.strip()
        if item:
            print(f"  {item}")

# 4. Now fix TB: delete old, re-copy, fix I0 reference
print("\n=== Fix TB ===")
# Delete old
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "a")
    when(cv dbDelete(cv) "DELETED" "NOT_FOUND"))
''', timeout=15)
print(f"  Delete: {r.output}")

# Copy
r = c.execute_skill(f'''
  let((src dst)
    src = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "r")
    dst = dbCopyCellView(src "{DST}" "ADC_9B_tb" "schematic" "" t)
    dbClose(src)
    dbClose(dst)
    "COPIED")
''', timeout=15)
print(f"  Copy: {r.output}")

# The copied TB still has SRC references. But since we're copying into a new library,
# dbCopyCellView should auto-remap references to cells that exist in DST.
# Let's check what happened
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
print("\n  TB instances (name|lib|cell):")
if r.output:
    for item in r.output.replace("(","").replace(")","").replace('"',"").split():
        item = item.strip()
        if item and '|' in item:
            parts = item.split('|')
            lib = parts[1] if len(parts) > 1 else "?"
            cell = parts[2] if len(parts) > 2 else "?"
            print(f"    {parts[0]:5s} | {lib} | {cell}")
