from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
SRC = "8BIT400MVcmredundancySAR"
DST = "SAR9B_400MV"

# 1. Check views of Verilog-A cells in source
print("=== Source cell views ===")
for cell in ["decode_redun9to8", "DAC8b_va"]:
    r = c.execute_skill(f'''
      let((cv views)
        cv = ddGetObj("{SRC}" "{cell}")
        views = nil
        when(cv
          foreach(v cv~>views
            views = cons(v~>name views)))
        views)
    ''', timeout=10)
    print(f"  {cell}: {r.output}")

# 2. Copy all views for Verilog-A cells
print("\n=== Copying Verilog-A cells ===")
for cell in ["decode_redun9to8", "DAC8b_va"]:
    r = c.execute_skill(f'''
      let((cv all_views)
        cv = ddGetObj("{SRC}" "{cell}")
        all_views = nil
        when(cv
          foreach(v cv~>views
            all_views = cons(v~>name all_views)))
        all_views)
    ''', timeout=10)
    if r.output:
        views = r.output.replace("(","").replace(")","").replace('"',"").split()
        for view in views:
            view = view.strip()
            if view:
                r2 = c.execute_skill(f'''
                  let((src_v dst_v)
                    src_v = dbOpenCellViewByType("{SRC}" "{cell}" "{view}" "" "r")
                    when(src_v
                      dst_v = dbCopyCellView(src_v "{DST}" "{cell}" "{view}" "" t)
                      dbClose(src_v)
                      dbClose(dst_v)
                      "{view}_COPIED"
                      "{view}_FAILED"))
                ''', timeout=15)
                print(f"  {cell}/{view}: {r2.output}")

# 3. Check TOP_9B_ADC views and capacitors
print("\n=== TOP_9B_ADC in SAR9B_400MV ===")
r = c.execute_skill(f'''
  let((cv views caps)
    cv = ddGetObj("{DST}" "TOP_9B_ADC")
    views = nil
    caps = nil
    when(cv
      foreach(v cv~>views
        views = cons(v~>name views)))
    ; check caps
    let((sch)
      sch = dbOpenCellViewByType("{DST}" "TOP_9B_ADC" "schematic" "" "r")
      when(sch
        foreach(inst sch~>instances
          when(inst~>cellName == "cap"
            caps = cons(strcat(inst~>name "=" inst~>c) caps)))
        dbClose(sch)))
    list(views caps))
''', timeout=10)
print(f"  Views: {r.output}")
print(f"  Caps: {r.output}")

# 4. Clean up old ADC_9B_tb and create fresh one
print("\n=== Refreshing ADC_9B_tb ===")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "a")
    when(cv
      dbDelete(cv)
      "DELETED"
      "NOT_FOUND"))
''', timeout=15)
print(f"  Delete old: {r.output}")

# Copy fresh from source
r = c.execute_skill(f'''
  let((src dst)
    src = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "r")
    dst = dbCopyCellView(src "{DST}" "ADC_9B_tb" "schematic" "" t)
    dbClose(src)
    dbClose(dst)
    "COPIED")
''', timeout=15)
print(f"  Copy TB: {r.output}")

# Check TB instances
r = c.execute_skill(f'''
  let((cv result)
    cv = dbOpenCellViewByType("{DST}" "ADC_9B_tb" "schematic" "" "r")
    result = nil
    when(cv
      foreach(inst cv~>instances
        result = cons(strcat(inst~>name ":" inst~>libName "/" inst~>cellName) result))
      dbClose(cv))
    result)
''', timeout=10)
if r.output:
    raw = r.output.replace("(","").replace(")","").replace('"',"").split()
    for item in sorted(raw):
        item = item.strip()
        if item and ':' in item:
            print(f"  {item}")
