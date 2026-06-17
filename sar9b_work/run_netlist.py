"""
Write netlist and run via Spectre using Maestro's simulation infrastructure.
"""
from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()

# We need the original input.scs from Maestro as a base
# Copy it, modify CDAC weights to binary, and run
#
# The ihdl netlists have the transistor-level subckts with all parasitics
# We can swap ONLY the capacitor values in the TOP subckt

LIB = "8BIT400MVcmredundancySAR"
TB = "ADC_redun1_tb"

# Path to working Maestro simulation
BASE = "/home/IC/simulation/8BIT400MVcmredundancySAR/ADC_redun1_tb/maestro/results/maestro/ExplorerRun.0"
SIM_DIR = f"{BASE}/psf/Vcmbased_ADC_tb_1/netlist"

# Download the 5 ihdl netlist files + input.scs
print("Downloading Maestro netlist files...")
import os
os.makedirs("E:/8bitvcmvirtuoso/sar9b_work/netlist_run", exist_ok=True)

for f in ["input.scs"] + [f"ihnl/cds{i}/netlist" for i in range(5)]:
    remote = f"{SIM_DIR}/{f}"
    local = f"E:/8bitvcmvirtuoso/sar9b_work/netlist_run/{f.replace('/', '_')}"
    try:
        c.download_file(remote, local)
        size = os.path.getsize(local)
        print(f"  {f}: {size} bytes")
    except Exception as e:
        print(f"  {f}: ERROR - {e}")

print("\nFiles downloaded to sar9b_work/netlist_run/")
