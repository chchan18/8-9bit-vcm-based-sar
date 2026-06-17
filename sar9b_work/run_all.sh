#!/bin/bash
set -e

WD=/home/IC/Desktop/Project/SAR9B_400MV/netlist_sim
SRC=/home/IC/simulation/8BIT400MVcmredundancySAR/ADC_redun1_tb/maestro/results/maestro/ExplorerRun.0

echo "=== 1. Re-copy original netlist ==="
cp "$SRC/psf/Vcmbased_ADC_tb_1/netlist/ihnl/cds16/netlist" "$WD/ihnl/cds16/netlist.orig"
echo "Original caps:"
grep 'capacitor c=' "$WD/ihnl/cds16/netlist.orig"

echo ""
echo "=== 2. Apply binary weight modifications ==="

python3 << 'PYEOF'
NETLIST = "/home/IC/Desktop/Project/SAR9B_400MV/netlist_sim/ihnl/cds16/netlist"
ORIG = NETLIST + ".orig"

import shutil
shutil.copy(ORIG, NETLIST)

with open(NETLIST, "r") as f:
    lines = f.readlines()

caps = {
    "C2":  "Cunit*256", "C17": "Cunit*256",
    "C0":  "Cunit*128", "C14": "Cunit*128",
    "C1":  "Cunit*64",  "C13": "Cunit*64",
    "C4":  "Cunit*32",  "C11": "Cunit*32",
    "C3":  "Cunit*16",  "C12": "Cunit*16",
    "C5":  "Cunit*8",   "C10": "Cunit*8",
    "C6":  "Cunit*4",   "C9":  "Cunit*4",
    "C7":  "Cunit*2",   "C8":  "Cunit*2",
}

modified = 0
for i, line in enumerate(lines):
    if "capacitor c=Cunit*" not in line:
        continue
    cap_name = line.strip().split()[0]
    if cap_name in caps:
        new_val = caps[cap_name]
        idx = line.find("capacitor c=")
        old_start = idx + len("capacitor c=")
        old_end = line.find(" ", old_start)
        if old_end < 0:
            old_end = len(line.rstrip())
        old_val = line[old_start:old_end]
        lines[i] = line[:old_start] + new_val + line[old_end:]
        modified += 1
        print("  %s: %s -> %s" % (cap_name, old_val, new_val))

with open(NETLIST, "w") as f:
    f.writelines(lines)

total = 0
print("\nFinal:")
for line in lines:
    if "capacitor c=" in line:
        name = line.strip().split()[0]
        val_str = line.split("capacitor c=")[1].split()[0].strip()
        val = int(val_str.replace("Cunit*", ""))
        total += val
        ok = "OK" if val_str == caps.get(name, val_str) else "MISMATCH"
        print("  %s = %s %s" % (name, val_str, ok))
    if "ends TOP" in line:
        break
print("Total per side: %d Cu" % (total // 2))
PYEOF

echo ""
echo "=== 3. Run spectre ==="
cd "$WD"
SPECTRE_DEFAULTS=-E \
/opt/eda/cadence/SPECTRE181/tools.lnx86/bin/spectre -64 input.scs \
    +escchars -format psfascii -raw raw_output \
    +aps +lqtimeout 900 -maxw 5 -maxn 5 \
    -ahdllibdir sharedData/CDS/ahdl/input.ahdlSimDB \
    +logstatus > spectre.log 2>&1 &

echo "Spectre started. PID: $!"
echo "Log: $WD/spectre.log"
