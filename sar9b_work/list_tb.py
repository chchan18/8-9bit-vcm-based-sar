from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
SRC = "8BIT400MVcmredundancySAR"

r = c.execute_skill(f'''
  let((cv result)
    cv = dbOpenCellViewByType("{SRC}" "ADC_redun1_tb" "schematic" "" "r")
    result = nil
    when(cv
      foreach(inst cv~>instances
        result = cons(strcat(inst~>name ":" inst~>cellName) result))
      dbClose(cv))
    result)
''', timeout=10)
if r.output:
    for item in sorted(r.output.replace("(","").replace(")","").replace('"',"").split()):
        if item.strip():
            print(item.strip())
