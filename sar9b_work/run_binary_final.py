"""
Final approach: ONLY modify CDAC weights (proven to work).
Run Maestro simulation with binary weights.
"""
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import open_gui_session, run_and_wait, close_gui_session
import time, sys

c = VirtuosoClient.from_env()
LIB = "8BIT400MVcmredundancySAR"
CELL = "TOP_redun1_ADC"
TB = "ADC_redun1_tb"

binary = {
    "C2":"Cunit*256","C17":"Cunit*256","C0":"Cunit*128","C14":"Cunit*128",
    "C1":"Cunit*64","C13":"Cunit*64","C4":"Cunit*32","C11":"Cunit*32",
    "C3":"Cunit*16","C12":"Cunit*16","C5":"Cunit*8","C10":"Cunit*8",
    "C6":"Cunit*4","C9":"Cunit*4","C7":"Cunit*2","C8":"Cunit*2",
}
original = {
    "C2":"Cunit*56","C17":"Cunit*56","C0":"Cunit*32","C14":"Cunit*32",
    "C1":"Cunit*18","C13":"Cunit*18","C4":"Cunit*10","C11":"Cunit*10",
    "C3":"Cunit*5","C12":"Cunit*5","C5":"Cunit*3","C10":"Cunit*3",
    "C6":"Cunit*2","C9":"Cunit*2","C7":"Cunit*1","C8":"Cunit*1",
}

def apply_weights(weights, label):
    for cap, val in weights.items():
        r = c.execute_skill(f'''
          let((cv inst)
            cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "a")
            inst = dbGetInstByName(cv "{cap}")
            when(inst inst~>c = "{val}")
            dbSave(cv) dbClose(cv) t)
        ''', timeout=10)
        if r.status.value != "success":
            print(f"  FAILED: {cap} -> {val}")
            return False
    print(f"  {label}: {len(weights)} caps OK")
    return True

# 1. Apply binary
print("Applying binary weights...")
if not apply_weights(binary, "Binary"):
    apply_weights(original, "Restore")
    sys.exit(1)

# 2. Open Maestro
print(f"\nOpening Maestro for {TB}...")
try:
    session = open_gui_session(c, LIB, TB)
    print(f"Session: {session}")

    print("\nRunning simulation (timeout=1800s)...")
    t0 = time.time()
    history, success = run_and_wait(c, session=session, timeout=1800)
    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.0f}s")

    if history:
        h = history.strip().strip('"')
        TEST = "Vcmbased_ADC_tb_1"
        print(f"\n=== RESULTS (history={h}) ===")
        r = c.execute_skill(f'maeOpenResults(?history "{h}")', timeout=15)
        for name in ["spectrum_enob", "spectrum_sinad", "vtime"]:
            r = c.execute_skill(f'maeGetOutputValue("{name}" "{TEST}" ?history "{h}")', timeout=15)
            if r.output:
                print(f"  {name} = {r.output}")
        c.execute_skill("maeCloseResults()", timeout=5)

    close_gui_session(c, session, save=False)
except Exception as e:
    print(f"ERROR: {e}")

# 3. ALWAYS restore
print("\nRestoring original weights...")
apply_weights(original, "Restored")
print("Done!")
