from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()

# Test 1: schCreateInst with simple coords
code1 = '''
  let((cv inst)
    cv = geOpen(?"8BIT400MVcmredundancySAR" "ADC_9B_tb_v3" "schematic" "a")
    inst = schCreateInst(cv "8BIT400MVcmredundancySAR" "TOP_9B_BINARY" "symbol" 0:0 "R0" "I0_TEST")
    when(inst
      dbSave(cv)
      list("CREATED" inst~>cellName)
      list("FAILED"))
    dbClose(cv))
'''
print("Test 1: geOpen + schCreateInst...")
r = c.execute_skill(code1, timeout=15)
print(f"  {r.status}: {r.output}")

# Test 2: dbCreateInst
code2 = '''
  let((cv inst lib cell)
    lib = ddGetObj("8BIT400MVcmredundancySAR")
    cell = ddGetObj(lib "TOP_9B_BINARY")
    cv = dbOpenCellViewByType("8BIT400MVcmredundancySAR" "ADC_9B_tb_v3" "schematic" "" "a")
    inst = dbCreateInst(cv cell "symbol" "I0_TEST2" 0:0 "R0")
    when(inst
      dbSave(cv)
      list("DB_CREATED" inst~>cellName)
      list("DB_FAILED"))
    dbClose(cv))
'''
print("\nTest 2: dbCreateInst with cell object...")
r = c.execute_skill(code2, timeout=15)
print(f"  {r.status}: {r.output}")

# Test 3: Copy existing instance approach
code3 = '''
  let((src_cv src_inst dst_cv dst_inst)
    src_cv = dbOpenCellViewByType("8BIT400MVcmredundancySAR" "ADC_redun1_tb" "schematic" "" "r")
    src_inst = dbGetInstByName(src_cv "I0")
    dst_cv = dbOpenCellViewByType("8BIT400MVcmredundancySAR" "ADC_9B_tb_v3" "schematic" "" "a")
    dst_inst = dbCopyInst(src_inst dst_cv nil "I0")
    dbClose(src_cv)
    when(dst_inst
      dst_inst~>master = ddGetObj("8BIT400MVcmredundancySAR" "TOP_9B_BINARY" "symbol")
      dbSave(dst_cv)
      list("COPY_AND_SWITCH" dst_inst~>cellName)
      list("COPY_FAILED"))
    dbClose(dst_cv))
'''
print("\nTest 3: Copy I0 from original TB + switch master...")
r = c.execute_skill(code3, timeout=15)
print(f"  {r.status}: {r.output}")
