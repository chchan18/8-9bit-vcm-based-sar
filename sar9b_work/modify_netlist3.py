#!/usr/bin/env python3
"""Atomic replacement using per-capacitor-name matching."""
NETLIST = "/home/IC/Desktop/Project/SAR9B_400MV/netlist_sim/ihnl/cds16/netlist"

# First, restore original file from backup or from Maestro
import shutil, os
BACKUP = NETLIST + ".orig"
if not os.path.exists(BACKUP):
    shutil.copy(NETLIST, BACKUP)
    print("Created backup: %s" % BACKUP)

# Start fresh from backup
shutil.copy(BACKUP, NETLIST)

with open(NETLIST, "r") as f:
    lines = f.readlines()

# Map each capacitor name to its new value
caps = {
    "C2":  "Cunit*256", "C17": "Cunit*256",  # bit8 MSB
    "C0":  "Cunit*128", "C14": "Cunit*128",  # bit7
    "C1":  "Cunit*64",  "C13": "Cunit*64",   # bit6
    "C4":  "Cunit*32",  "C11": "Cunit*32",   # bit5
    "C3":  "Cunit*16",  "C12": "Cunit*16",   # bit4
    "C5":  "Cunit*8",   "C10": "Cunit*8",    # bit3
    "C6":  "Cunit*4",   "C9":  "Cunit*4",    # bit2
    "C7":  "Cunit*2",   "C8":  "Cunit*2",    # bit1
    # C15, C16: no change (stay at Cunit*1 for bit0 LSB)
}

modified = 0
for i, line in enumerate(lines):
    if "capacitor c=Cunit*" not in line:
        continue

    # Extract capacitor name from "    C15 (net14 net15) capacitor c=..."
    cap_name = line.strip().split()[0]  # e.g. "C15"

    if cap_name in caps:
        new_val = caps[cap_name]
        # Find old value
        idx = line.find("capacitor c=")
        old_start = idx + len("capacitor c=")
        old_end = line.find(" ", old_start)
        if old_end < 0:
            old_end = len(line.rstrip())
        old_val = line[old_start:old_end]

        # Replace
        lines[i] = line[:old_start] + new_val + line[old_end:]
        modified += 1
        print("  %s: %s -> %s" % (cap_name, old_val, new_val))

with open(NETLIST, "w") as f:
    f.writelines(lines)

# Verify
print("\nFinal capacitors:")
total = 0
with open(NETLIST) as f:
    for line in f:
        if "capacitor c=" in line:
            name = line.strip().split()[0]
            val_str = line.split("capacitor c=")[1].split()[0].strip()
            val = int(val_str.replace("Cunit*", ""))
            total += val
            flag = " OK" if val_str == caps.get(name, val_str) else ""
            print("  %s = %s (%d Cu)%s" % (name, val_str, val, flag))
        if "ends TOP" in line:
            break

print("\nTotal per side: %d Cu (should be 511)" % (total // 2))
print("Modified: %d capacitors" % modified)
