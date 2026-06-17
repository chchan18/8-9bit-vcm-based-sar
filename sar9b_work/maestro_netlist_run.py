"""
Create a Maestro testbench using the EXISTING working ADC_redun1_tb Maestro.
Instead of modifying the schematic, we:
1. Modify TOP_redun1_ADC CDAC to binary (temporarily, restore after)
2. Run the Maestro simulation which auto-generates proper netlists
3. Get results, restore weights
"""
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro import open_gui_session, run_and_wait, close_gui_session, save_setup
import time

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
original_weights = {
    "C2":"Cunit*56","C17":"Cunit*56","C0":"Cunit*32","C14":"Cunit*32",
    "C1":"Cunit*18","C13":"Cunit*18","C4":"Cunit*10","C11":"Cunit*10",
    "C3":"Cunit*5","C12":"Cunit*5","C5":"Cunit*3","C10":"Cunit*3",
    "C6":"Cunit*2","C9":"Cunit*2","C7":"Cunit*1","C8":"Cunit*1",
}

# 1. Apply binary weights
print("Applying binary CDAC weights...")
for cap, val in binary.items():
    c.execute_skill(f'''
      let((cv inst)
        cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "a")
        inst = dbGetInstByName(cv "{cap}")
        when(inst inst~>c = "{val}")
        dbSave(cv) dbClose(cv) t)
    ''', timeout=10)
print("Done.")

# 2. Open Maestro and run with LONGER timeout
print(f"\nOpening Maestro for {TB}...")
try:
    session = open_gui_session(c, LIB, TB)
    print(f"Session: {session}")

    # Set shorter TSTOP for faster sim, or keep same
    print("\nRunning simulation (binary 9-bit, timeout=1800s)...")
    t0 = time.time()
    history, success = run_and_wait(c, session=session, timeout=1800)
    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.0f}s, History: {history}")

    if history:
        h = history.strip().strip('"')
        TEST = "Vcmbased_ADC_tb_1"
        print(f"\nResults (history={h}):")
        for name in ["spectrum_enob", "spectrum_sinad"]:
            r = c.execute_skill(f'maeGetOutputValue("{name}" "{TEST}" ?history "{h}")', timeout=15)
            print(f"  {name} = {r.output}")
        c.execute_skill("maeCloseResults()", timeout=5)
    else:
        print("No history returned - simulation may have failed.")

    close_gui_session(c, session, save=False)
except Exception as e:
    print(f"ERROR: {e}")

# 3. ALWAYS restore original weights
print("\nRestoring original weights...")
for cap, val in original_weights.items():
    c.execute_skill(f'''
      let((cv inst)
        cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "a")
        inst = dbGetInstByName(cv "{cap}")
        when(inst inst~>c = "{val}")
        dbSave(cv) dbClose(cv) t)
    ''', timeout=10)
print("Restored.")
print("\nDone!")
