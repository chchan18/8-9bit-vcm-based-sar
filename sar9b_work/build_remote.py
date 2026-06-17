#!/usr/bin/env python3
"""Build standalone netlist on remote, run spectre."""
import os, re, shutil

PDK = "/home/IC/Desktop/Project/project_tsmcN28_NEW/project_tsmcN28_NEW/iPDK_CRN28HPC+_v1.0_2p2a_20160226_all/CRN28HPCp/models/spectre"
SRC = "/home/IC/simulation/8BIT400MVcmredundancySAR/ADC_redun1_tb/maestro/results/maestro/ExplorerRun.0/psf/Vcmbased_ADC_tb_1/netlist"
WD = "/home/IC/Desktop/Project/SAR9B_400MV/netlist_standalone"

os.makedirs(WD, exist_ok=True)

# 1. Copy input.scs
shutil.copy(f"{SRC}/input.scs", f"{WD}/input.scs")

# 2. Replace PDK include
with open(f"{WD}/input.scs") as f:
    content = f.read()

old = f'include "{PDK}/toplevel.scs"'
new = f"""simulator lang=spectre insensitive=yes
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=ttmacro_mos_moscap
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=tt_res_bip_dio_disres
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=tt_mom
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=tt_r_metal
include "{PDK}/cln28hpcp_hv_1d8_elk_v0d1_2p1_shrink0d9_embedded_usage.scs" section=ttmacro_mos_moscap"""

content = content.replace(old, new)
print("Replaced PDK include")

# 3. Add ihdl includes (just the first few that have all subckts)
out = content
for i in range(5):  # cds0-cds4 cover all subckts
    out += f'\ninclude "{SRC}/ihnl/cds{i}/netlist"\n'

# 4. Write final netlist
with open(f"{WD}/netlist_9b.scs", "w") as f:
    f.write(out)

# 5. Copy and modify CDAC weights in the TOP subckt file
shutil.copy(f"{SRC}/ihnl/cds16/netlist", f"{WD}/top_subckt.scs")

with open(f"{WD}/top_subckt.scs") as f:
    top_lines = f.readlines()

caps = {
    "C2":"Cunit*256","C17":"Cunit*256",
    "C0":"Cunit*128","C14":"Cunit*128",
    "C1":"Cunit*64","C13":"Cunit*64",
    "C4":"Cunit*32","C11":"Cunit*32",
    "C3":"Cunit*16","C12":"Cunit*16",
    "C5":"Cunit*8","C10":"Cunit*8",
    "C6":"Cunit*4","C9":"Cunit*4",
    "C7":"Cunit*2","C8":"Cunit*2",
}

for i, line in enumerate(top_lines):
    if "capacitor c=Cunit*" not in line:
        continue
    cap_name = line.strip().split()[0]
    if cap_name in caps:
        new_val = caps[cap_name]
        idx = line.find("capacitor c=")
        old_start = idx + len("capacitor c=")
        old_end = line.find(" ", old_start)
        if old_end < 0: old_end = len(line.rstrip())
        old_val = line[old_start:old_end]
        top_lines[i] = line[:old_start] + new_val + line[old_end:]

with open(f"{WD}/top_subckt.scs", "w") as f:
    f.writelines(top_lines)

# Verify
total = 0
for line in top_lines:
    if "capacitor c=" in line:
        v = int(line.split("capacitor c=Cunit*")[1].split()[0])
        total += v
print(f"CDAC total per side: {total//2} Cu (should be 511)")

# 6. Build final: input.scs (with PDK fix) + top_subckt + other ihdl
with open(f"{WD}/netlist_final.scs", "w") as f:
    f.write(content)  # modified input.scs
    # Include binary CDAC subckt instead of cds16
    f.write(f'\ninclude "{WD}/top_subckt.scs"\n')
    # Include other ihdl files (skip cds16 since we have top_subckt)
    for i in range(5):
        if i != 16 % 5:  # just include all 5; duplicates will error
            pass
    f.write(f'\ninclude "{SRC}/ihnl/cds0/netlist"\n')
    f.write(f'\ninclude "{SRC}/ihnl/cds1/netlist"\n')
    f.write(f'\ninclude "{SRC}/ihnl/cds2/netlist"\n')
    f.write(f'\ninclude "{SRC}/ihnl/cds3/netlist"\n')
    f.write(f'\ninclude "{SRC}/ihnl/cds4/netlist"\n')

# Need to handle cds16 specially: replace its include with our modified top_subckt
# Actually, cds16 has TOP_redun1_ADC which is already included via cds16 netlist
# Our top_subckt.scs replaces it

print(f"Wrote: {WD}/netlist_final.scs")

# 7. Copy Verilog-A files
shutil.copy(f"{PDK}/../../../../../../../8BIT400MVcmredundancySAR/DAC8b_va/veriloga/veriloga.va", f"{WD}/dac8b.va")
shutil.copy(f"{PDK}/../../../../../../../8BIT400MVcmredundancySAR/decode_redun9to8/veriloga/veriloga.va", f"{WD}/decode.va")

# 8. Copy AHDL database
AHDL_SRC = "/home/IC/simulation/8BIT400MVcmredundancySAR/ADC_redun1_tb/maestro/results/maestro/ExplorerRun.0/sharedData"
shutil.copytree(AHDL_SRC, f"{WD}/sharedData", dirs_exist_ok=True)

print("Ready to run.")
print(f"cd {WD} && SPECTRE_DEFAULTS=-E spectre -64 netlist_final.scs ...")
