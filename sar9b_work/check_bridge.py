from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()

# Basic test
r = c.execute_skill("1+2", timeout=5)
print(f"1+2: {r.output} ({r.status})")

# Check original TB
r = c.execute_skill('''
  let((cv)
    cv = dbOpenCellViewByType("8BIT400MVcmredundancySAR" "ADC_redun1_tb" "schematic" "" "r")
    length(cv~>instances))
''', timeout=10)
print(f"Original TB instances: {r.output} ({r.status})")

# Check new TB
r = c.execute_skill('''
  let((cv)
    cv = dbOpenCellViewByType("8BIT400MVcmredundancySAR" "ADC_9B_tb_v3" "schematic" "" "r")
    when(cv
      length(cv~>instances)
      "CELL_NOT_FOUND"))
''', timeout=10)
print(f"New TB instances: {r.output} ({r.status})")

# Check if TOP_9B_BINARY can be opened
r = c.execute_skill('''
  let((cv)
    cv = dbOpenCellViewByType("8BIT400MVcmredundancySAR" "TOP_9B_BINARY" "symbol" "" "r")
    when(cv
      list(cv~>cellName length(cv~>terminals))
      "NO_SYMBOL"))
''', timeout=10)
print(f"Symbol: {r.output} ({r.status})")
