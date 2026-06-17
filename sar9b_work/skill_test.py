"""Step-by-step SKILL testing for GUI operations."""
from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"

# Test 1: Basic SKILL
print("=== Test 1: Basic SKILL ===")
r = c.execute_skill("1+2", timeout=5)
print(f"  1+2 = {r.output}")

# Test 2: Open schematic
print("\n=== Test 2: Open schematic ===")
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{LIB}" "ADC_redun1_tb" "schematic" "" "a")
    when(cv
      list(length(cv~>instances))
      "OPEN_FAILED"))
''', timeout=10)
print(f"  Instances: {r.output}")

# Test 3: Read I0 properties
print("\n=== Test 3: Read I0 ===")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "ADC_redun1_tb" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    when(inst
      list(inst~>cellName inst~>libName inst~>viewName inst~>xy))
    dbClose(cv))
''', timeout=10)
print(f"  I0: {r.output}")

# Test 4: Read I14 (decode)
print("\n=== Test 4: Read I14 ===")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "ADC_redun1_tb" "schematic" "" "r")
    inst = dbGetInstByName(cv "I14")
    when(inst
      list(inst~>cellName inst~>libName))
    dbClose(cv))
''', timeout=10)
print(f"  I14: {r.output}")

# Test 5: Read I15 (DAC)
print("\n=== Test 5: Read I15 (DAC) ===")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "ADC_redun1_tb" "schematic" "" "r")
    inst = dbGetInstByName(cv "I15")
    when(inst
      let((terms)
        terms = nil
        foreach(t inst~>instTerms
          terms = cons(strcat(t~>name "->" t~>net~>name) terms))
        terms))
    dbClose(cv))
''', timeout=10)
print(f"  I15 terminals: {r.output}")

# Test 6: Try schReplaceInst on I0
print("\n=== Test 6: schReplaceInst I0 -> TOP_9B_BINARY ===")
# First check if TOP_9B_BINARY symbol exists
r = c.execute_skill(f'''
  let((cv)
    cv = dbOpenCellViewByType("{LIB}" "TOP_9B_BINARY" "symbol" "" "r")
    when(cv
      dbClose(cv)
      "HAS_SYMBOL"
      "NO_SYMBOL"))
''', timeout=10)
print(f"  TOP_9B_BINARY symbol: {r.output}")

# Now try the replace
r = c.execute_skill(f'''
  let((cv inst newMaster result)
    cv = dbOpenCellViewByType("{LIB}" "ADC_redun1_tb" "schematic" "" "a")
    inst = dbGetInstByName(cv "I0")
    when(inst
      newMaster = dbOpenCellViewByType("{LIB}" "TOP_9B_BINARY" "symbol")
      when(newMaster
        result = schReplaceInst(inst newMaster)
        dbSave(cv)
        list("REPLACED" result inst~>cellName))
      dbClose(newMaster))
    dbClose(cv))
''', timeout=15)
print(f"  Replace result: {r.output}")
print(f"  Status: {r.status}")

# Test 7: Verify I0 after replace
print("\n=== Test 7: Verify I0 ===")
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{LIB}" "ADC_redun1_tb" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    when(inst
      list(inst~>cellName inst~>libName))
    dbClose(cv))
''', timeout=10)
print(f"  I0 after: {r.output}")
