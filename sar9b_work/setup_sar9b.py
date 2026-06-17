from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
SRC = "8BIT400MVcmredundancySAR"
DST = "SAR9B_400MV"

# 1. Check what's already in SAR9B_400MV
print("=== SAR9B_400MV contents ===")
r = c.execute_skill(f'''
  let((lib cells)
    lib = ddGetObj("{DST}")
    cells = nil
    foreach(cell lib~>cells
      cells = cons(cell~>name cells))
    cells)
''', timeout=10)
dst_cells = set()
if r.output:
    raw = r.output.replace("(","").replace(")","").replace('"',"").split()
    dst_cells = {x.strip() for x in raw if x.strip()}
    for cell in sorted(dst_cells):
        print(f"  {cell}")

# 2. What we need for the TB
needed = [
    "INVX1", "INVX2", "INVX4", "INVX8",
    "NAND2X1", "NOR2X1", "TRIGATEX1", "DELAY_1",
    "OR3X1", "DFF", "DFFRN",
    "BOOTSTRAP_DIFF", "CLK_NOOVERLAP", "COMPARATOR",
    "Asycontrol_logic_9clk", "control",
    "TOP_9B_ADC",  # ADC (already created, maybe needs symbol)
    "decode_redun9to8",  # For TB
    "DAC8b_va",  # For TB (we'll work with 8-bit DAC for now)
]

print("\n=== Missing cells ===")
missing = [c for c in needed if c not in dst_cells]
for m in missing:
    print(f"  {m}")

# 3. Copy missing cells
print(f"\n=== Copying {len(missing)} missing cells ===")
for cell in missing:
    r = c.execute_skill(f'''
      let((src_cv dst_cv)
        src_cv = dbOpenCellViewByType("{SRC}" "{cell}" "schematic" "" "r")
        when(src_cv
          dst_cv = dbCopyCellView(src_cv "{DST}" "{cell}" "schematic" "" t)
          dbClose(dst_cv)
          dbClose(src_cv)
          "{cell}_COPIED"
          "{cell}_NOT_FOUND"))
    ''', timeout=15)
    print(f"  {cell}: {r.output}")

# Also copy symbol views for cells that need them
print("\n=== Copying symbol views ===")
for cell in ["TOP_9B_ADC"] + missing:
    # Check if cell has symbol in source
    r = c.execute_skill(f'''
      let((cv)
        cv = dbOpenCellViewByType("{SRC}" "{cell}" "symbol" "" "r")
        when(cv
          dbClose(cv)
          "HAS_SYMBOL"
          "NO_SYMBOL"))
    ''', timeout=10)
    if r.output == '"HAS_SYMBOL"':
        r2 = c.execute_skill(f'''
          let((src_sym dst_sym)
            src_sym = dbOpenCellViewByType("{SRC}" "{cell}" "symbol" "" "r")
            dst_sym = dbCopyCellView(src_sym "{DST}" "{cell}" "symbol" "" t)
            dbClose(src_sym)
            dbClose(dst_sym)
            "OK")
        ''', timeout=15)
        print(f"  {cell} symbol: copied")

print("\nDone copying.")
