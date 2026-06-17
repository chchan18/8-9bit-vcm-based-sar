"""Check and restore TB state."""
from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
SRC = "8BIT400MVcmredundancySAR"

# Check TB
r = c.execute_skill(f'''
  let((cv count)
    cv = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "r")
    count = nil
    when(cv
      count = length(cv~>instances)
      dbClose(cv))
    count)
''', timeout=10)
print(f"TB instances: {r.output}")

# Check I0
r = c.execute_skill(f'''
  let((cv inst)
    cv = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "r")
    inst = dbGetInstByName(cv "I0")
    dbClose(cv)
    when(inst list(inst~>cellName) "I0_MISSING"))
''', timeout=10)
print(f"I0: {r.output}")
