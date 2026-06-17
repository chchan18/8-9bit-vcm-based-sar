"""Debug and fix SKILL issues."""
from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
SRC = "8BIT400MVcmredundancySAR"
DST = "SAR9B_400MV"

# Fix 1: Purge locks
print("=== Fix 1: Purge locks ===")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "a")
    when(cv
      dbClose(cv)
      list("OPEN_OK" cv~>cellName)
      list("OPEN_FAILED")))
''', timeout=10)
print(f"  Open 'a' mode: {r.output}")

# If failed, try purging
if "FAILED" in str(r.output):
    print("  Purging locks...")
    # Delete lock file
    r = c.execute_skill('''
      let((cv)
        cv = dbOpenCellViewByType("8BIT400MVcmredundancySAR" "ADC_redun1_tb" "schematic" "" "a")
        dbPurge(cv)
        dbClose(cv)
        "PURGED")
    ''', timeout=10)
    print(f"  Purge: {r.output}")

    # Retry
    r = c.execute_skill(f'''
      let((cv)
        cv = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "a")
        when(cv
          dbClose(cv)
          "OPEN_OK_AFTER_PURGE"
          "STILL_FAILED"))
    ''', timeout=10)
    print(f"  Retry: {r.output}")

# Fix 2: Check SAR9B_400MV/TOP_9B_ADC symbol
print("\n=== Fix 2: Check DST symbol ===")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{DST}" "TOP_9B_ADC" "symbol" "" "r")
    when(cv
      list(cv~>cellName length(cv~>terminals))
      "NO_SYMBOL"))
''', timeout=10)
print(f"  TOP_9B_ADC symbol: {r.output}")

# Fix 3: Properly return I0 data
print("\n=== Fix 3: Proper I0 read ===")
r = c.execute_skill(f'''
  let((cv inst result)
    cv = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    result = nil
    when(inst
      result = list(inst~>cellName inst~>libName))
    dbClose(cv)
    result)
''', timeout=10)
print(f"  I0: {r.output}")

# Fix 4: Check if schReplaceInst works between libraries
print("\n=== Fix 4: Cross-library replace ===")
r = c.execute_skill(f'''
  let((cv inst newM)
    cv = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "a")
    inst = dbGetInstByName(cv "I0")
    newM = dbOpenCellViewByType("{DST}" "TOP_9B_ADC" "symbol")
    when(inst && newM
      schReplaceInst(inst newM)
      dbSave(cv)
      list(inst~>cellName inst~>libName))
    dbClose(cv)
    dbClose(newM))
''', timeout=15)
print(f"  Replace: status={r.status}, output={r.output}")

# Fix 5: Verify
print("\n=== Fix 5: Verify after replace ===")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    dbClose(cv)
    when(inst list(inst~>cellName inst~>libName) "I0_NOT_FOUND"))
''', timeout=10)
print(f"  I0: {r.output}")
