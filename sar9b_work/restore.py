from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"
CELL = "TOP_redun1_ADC"

original = {
    "C2":"Cunit*56","C17":"Cunit*56",
    "C0":"Cunit*32","C14":"Cunit*32",
    "C1":"Cunit*18","C13":"Cunit*18",
    "C4":"Cunit*10","C11":"Cunit*10",
    "C3":"Cunit*5","C12":"Cunit*5",
    "C5":"Cunit*3","C10":"Cunit*3",
    "C6":"Cunit*2","C9":"Cunit*2",
    "C7":"Cunit*1","C8":"Cunit*1",
    "C15":"Cunit*1","C16":"Cunit*1",
}

for cap, val in original.items():
    r = c.execute_skill(f'''
      let((cv inst)
        cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "a")
        inst = dbGetInstByName(cv "{cap}")
        when(inst
          inst~>c = "{val}")
        dbSave(cv)
        dbClose(cv)
        t)
    ''', timeout=10)
    print(f"  {cap} -> {val}: {r.status}")

r = c.execute_skill(f'''
  let((cv caps)
    cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "r")
    caps = nil
    foreach(inst cv~>instances
      when(inst~>cellName == "cap"
        caps = cons(strcat(inst~>name "=" inst~>c) caps)))
    dbClose(cv)
    caps)
''', timeout=10)
print(f"Restored: {r.output}")
