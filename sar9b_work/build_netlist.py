"""
Build complete standalone spectre netlist for 9-bit binary SAR ADC.
Uses direct PDK model includes (bypasses library statement).
"""
from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()

# Download the Maestro input.scs as base
SRC = "/home/IC/simulation/8BIT400MVcmredundancySAR/ADC_redun1_tb/maestro/results/maestro/ExplorerRun.0/psf/Vcmbased_ADC_tb_1/netlist"

print("Downloading netlist files...")
import os
os.makedirs("E:/8bitvcmvirtuoso/sar9b_work/netlist_final", exist_ok=True)

# Download input.scs
c.download_file(f"{SRC}/input.scs", "E:/8bitvcmvirtuoso/sar9b_work/netlist_final/input.scs")

# Download the ihdl file with TOP subckt
for i in range(5):
    try:
        c.download_file(f"{SRC}/ihnl/cds{i}/netlist", f"E:/8bitvcmvirtuoso/sar9b_work/netlist_final/ihnl_cds{i}.scs")
    except:
        pass

# Download a few more to find all subckts
for i in range(5, 20):
    try:
        c.download_file(f"{SRC}/ihnl/cds{i}/netlist", f"E:/8bitvcmvirtuoso/sar9b_work/netlist_final/ihnl_cds{i}.scs")
    except:
        break

print("Downloaded.")

# Read input.scs
with open("E:/8bitvcmvirtuoso/sar9b_work/netlist_final/input.scs") as f:
    input_scs = f.read()

# Replace toplevel.scs include with direct model includes
PDK = "/home/IC/Desktop/Project/project_tsmcN28_NEW/project_tsmcN28_NEW/iPDK_CRN28HPC+_v1.0_2p2a_20160226_all/CRN28HPCp/models/spectre"

old_include = f'include "{PDK}/toplevel.scs"'
new_includes = f"""simulator lang=spectre insensitive=yes
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=ttmacro_mos_moscap
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=tt_res_bip_dio_disres
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=tt_mom
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=tt_r_metal
include "{PDK}/cln28hpcp_hv_1d8_elk_v0d1_2p1_shrink0d9_embedded_usage.scs" section=ttmacro_mos_moscap"""

input_scs = input_scs.replace(old_include, new_includes)
print("Replaced PDK include")

# Find the TOP_redun1_ADC subckt and modify CDAC to binary
# The TOP subckt is in ihnl_cds16.scs
top_file = "E:/8bitvcmvirtuoso/sar9b_work/netlist_final/ihnl_cds16.scs"
try:
    with open(top_file) as f:
        top_content = f.read()

    # Modify CDAC capacitors
    caps = {
        "C2": "Cunit*256", "C17": "Cunit*256",
        "C0": "Cunit*128", "C14": "Cunit*128",
        "C1": "Cunit*64",  "C13": "Cunit*64",
        "C4": "Cunit*32",  "C11": "Cunit*32",
        "C3": "Cunit*16",  "C12": "Cunit*16",
        "C5": "Cunit*8",   "C10": "Cunit*8",
        "C6": "Cunit*4",   "C9":  "Cunit*4",
        "C7": "Cunit*2",   "C8":  "Cunit*2",
    }

    import re
    for cap_name, new_val in caps.items():
        # Match: "    C15 (net14 net15) capacitor c=OLD"
        pattern = re.compile(rf"(\s+{cap_name}\s+\(.*?capacitor c=)[^\s]+")
        top_content = pattern.sub(rf"\g<1>{new_val}", top_content)

    with open(top_file, "w") as f:
        f.write(top_content)
    print("Modified CDAC to binary weights")
except Exception as e:
    print(f"CDAC modification error: {e}")

# Build final standalone netlist
print("\nBuilding final netlist...")
with open("E:/8bitvcmvirtuoso/sar9b_work/netlist_final/netlist_9b.scs", "w") as out:
    # Write the modified input.scs
    out.write(input_scs)
    out.write("\n")

    # Include all ihdl netlist files (these have the transistor subckts)
    for i in range(20):
        ihdl_file = f"E:/8bitvcmvirtuoso/sar9b_work/netlist_final/ihnl_cds{i}.scs"
        if os.path.exists(ihdl_file):
            with open(ihdl_file) as f:
                out.write(f"\n// === ihnl_cds{i} ===\n")
                out.write(f.read())
            print(f"  Added ihnl_cds{i}.scs")

print("Done. Written to netlist_final/netlist_9b.scs")
