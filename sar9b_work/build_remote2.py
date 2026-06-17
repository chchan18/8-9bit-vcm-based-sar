#!/usr/bin/env python3
"""Build standalone netlist. Minimal, correct approach."""
import os, shutil

PDK = "/home/IC/Desktop/Project/project_tsmcN28_NEW/project_tsmcN28_NEW/iPDK_CRN28HPC+_v1.0_2p2a_20160226_all/CRN28HPCp/models/spectre"
SRC = "/home/IC/simulation/8BIT400MVcmredundancySAR/ADC_redun1_tb/maestro/results/maestro/ExplorerRun.0/psf/Vcmbased_ADC_tb_1/netlist"
WD = "/home/IC/Desktop/Project/SAR9B_400MV/netlist_standalone"
os.makedirs(WD, exist_ok=True)

# 1. Read input.scs
with open(f"{SRC}/input.scs") as f:
    content = f.read()

# 2. Replace PDK toplevel.scs with direct model includes
old_pdk = f'include "{PDK}/toplevel.scs"'
new_pdk = f"""simulator lang=spectre insensitive=yes
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=ttmacro_mos_moscap
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=tt_res_bip_dio_disres
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=tt_mom
include "{PDK}/crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs" section=tt_r_metal
include "{PDK}/cln28hpcp_hv_1d8_elk_v0d1_2p1_shrink0d9_embedded_usage.scs" section=ttmacro_mos_moscap"""
content = content.replace(old_pdk, new_pdk)

# 3. Copy & modify TOP subckt (cds16) -> binary CDAC
shutil.copy(f"{SRC}/ihnl/cds16/netlist", f"{WD}/top_binary.scs")
with open(f"{WD}/top_binary.scs") as f:
    top = f.readlines()

caps = {"C2":"Cunit*256","C17":"Cunit*256","C0":"Cunit*128","C14":"Cunit*128",
        "C1":"Cunit*64","C13":"Cunit*64","C4":"Cunit*32","C11":"Cunit*32",
        "C3":"Cunit*16","C12":"Cunit*16","C5":"Cunit*8","C10":"Cunit*8",
        "C6":"Cunit*4","C9":"Cunit*4","C7":"Cunit*2","C8":"Cunit*2"}

for i, line in enumerate(top):
    if "capacitor c=Cunit*" in line:
        cap = line.strip().split()[0]
        if cap in caps:
            start = line.find("capacitor c=") + len("capacitor c=")
            end = line.find(" ", start)
            if end < 0: end = len(line.rstrip())
            top[i] = line[:start] + caps[cap] + line[end:]

with open(f"{WD}/top_binary.scs", "w") as f:
    f.writelines(top)

# Verify
total = sum(int(l.split("capacitor c=Cunit*")[1].split()[0]) for l in top if "capacitor c=" in l)
print(f"CDAC total per side: {total//2} Cu (should be 511)")

# 4. Build final netlist
with open(f"{WD}/netlist_9b.scs", "w") as f:
    f.write(content)
    f.write("\n")
    # Include all ihdl files from cds0 to cds18 (skip cds16 - use our binary version)
    for i in range(19):
        cds_file = f"{SRC}/ihnl/cds{i}/netlist"
        if os.path.exists(cds_file):
            if i == 16:
                f.write(f'\ninclude "{WD}/top_binary.scs"\n')
            else:
                f.write(f'\ninclude "{cds_file}"\n')
    f.write("\n")

# 5. Copy AHDL and VA files
shutil.copytree(f"{SRC}/../../sharedData", f"{WD}/sharedData", dirs_exist_ok=True)
for va_cell in ["DAC8b_va", "decode_redun9to8"]:
    va_file = f"/home/IC/Desktop/Project/8BIT400MVcmredundancySAR/{va_cell}/veriloga/veriloga.va"
    if os.path.exists(va_file):
        shutil.copy(va_file, f"{WD}/{va_cell}.va")

print(f"\nNetlist: {WD}/netlist_9b.scs")
print(f"Run: cd {WD} && SPECTRE_DEFAULTS=-E spectre -64 netlist_9b.scs +escchars -format psfascii -raw raw +aps +lqtimeout 900 -maxw 5 -maxn 5 -ahdllibdir sharedData/CDS/ahdl/input.ahdlSimDB +logstatus")
