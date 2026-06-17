"""
Modify TOP_redun1_ADC CDAC to binary, run Maestro simulation, restore.
"""
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import (
    open_gui_session, close_gui_session, run_and_wait, save_setup
)
import time

c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"
CELL = "TOP_redun1_ADC"
TB = "ADC_redun1_tb"

# 1. Save original CDAC weights
print("1. Saving original weights...")
r = c.execute_skill(f'''
  let((cv caps)
    cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "r")
    caps = nil
    when(cv
      foreach(inst cv~>instances
        when(inst~>cellName == "cap"
          caps = cons(strcat(inst~>name "=" inst~>c) caps)))
      dbClose(cv))
    caps)
''', timeout=10)
original = {}
for item in (r.output or "").replace("(","").replace(")","").replace('"',"").split():
    if "=" in item:
        name, val = item.split("=", 1)
        original[name.strip()] = val.strip()
print(f"   Saved {len(original)} caps")

# 2. Apply binary weights
print("\n2. Applying binary weights...")
binary = {
    "C2":  "Cunit*256", "C17": "Cunit*256",
    "C0":  "Cunit*128", "C14": "Cunit*128",
    "C1":  "Cunit*64",  "C13": "Cunit*64",
    "C4":  "Cunit*32",  "C11": "Cunit*32",
    "C3":  "Cunit*16",  "C12": "Cunit*16",
    "C5":  "Cunit*8",   "C10": "Cunit*8",
    "C6":  "Cunit*4",   "C9":  "Cunit*4",
    "C7":  "Cunit*2",   "C8":  "Cunit*2",
}
for cap_name, new_val in binary.items():
    r = c.execute_skill(f'''
      let((cv inst)
        cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "a")
        inst = dbGetInstByName(cv "{cap_name}")
        when(inst
          inst~>c = "{new_val}")
        dbSave(cv)
        dbClose(cv)
        t)
    ''', timeout=10)
    print(f"   {cap_name}: {original.get(cap_name,'?')} -> {new_val}")

# 3. Verify
print("\n3. Verification:")
r = c.execute_skill(f'''
  let((cv caps total)
    cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "r")
    caps = nil
    total = 0
    when(cv
      foreach(inst cv~>instances
        when(inst~>cellName == "cap"
          let((val)
            val = inst~>c
            caps = cons(strcat(inst~>name "=" val) caps)
            when(val && strcat(val) != ""
              val = cdfParseFloatString(cadr(parseString(val)))
              total = total + val))))
      dbClose(cv))
    list(caps total))
''', timeout=10)
print(f"   {r.output}")

# 4. Open Maestro and run
print(f"\n4. Opening Maestro for {TB}...")
try:
    session = open_gui_session(c, LIB, TB)
    print(f"   Session: {session}")

    print("\n5. Running simulation (binary 9-bit, TSTOP=2.7us)...")
    t0 = time.time()
    history, success = run_and_wait(c, session=session, timeout=600)
    elapsed = time.time() - t0
    print(f"   Completed in {elapsed:.0f}s, History: {history}")

    if history:
        h = history.strip().strip('"')
        TEST = "Vcmbased_ADC_tb_1"
        print(f"\n6. Results:")
        for name in ["spectrum_enob", "spectrum_sinad"]:
            r = c.execute_skill(f'maeGetOutputValue("{name}" "{TEST}" ?history "{h}")', timeout=15)
            print(f"   {name} = {r.output}")
        c.execute_skill("maeCloseResults()", timeout=5)

    close_gui_session(c, session, save=False)
except Exception as e:
    print(f"   ERROR: {e}")

# 5. Restore original weights
print("\n7. Restoring original weights...")
for cap_name, old_val in original.items():
    if cap_name in binary:  # only restore what we changed
        r = c.execute_skill(f'''
          let((cv inst)
            cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "a")
            inst = dbGetInstByName(cv "{cap_name}")
            when(inst
              inst~>c = "{old_val}")
            dbSave(cv)
            dbClose(cv)
            t)
        ''', timeout=10)
        print(f"   {cap_name}: restored to {old_val}")

print("\nDone!")
