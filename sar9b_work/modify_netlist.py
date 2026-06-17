#!/usr/bin/env python3
"""Modify TOP CDAC weights from redundant to binary using simple string replace."""
import sys

NETLIST = "/home/IC/Desktop/Project/SAR9B_400MV/netlist_sim/ihnl/cds16/netlist"

with open(NETLIST, "r") as f:
    lines = f.readlines()

# Each capacitor line looks like:
#     C15 (net14 net15) capacitor c=Cunit*1
# We replace the c= value based on capacitor name

caps = {
    "C2":  "Cunit*256", "C17": "Cunit*256",  # bit8 MSB
    "C0":  "Cunit*128", "C14": "Cunit*128",  # bit7
    "C1":  "Cunit*64",  "C13": "Cunit*64",   # bit6
    "C4":  "Cunit*32",  "C11": "Cunit*32",   # bit5
    "C3":  "Cunit*16",  "C12": "Cunit*16",   # bit4
    "C5":  "Cunit*8",   "C10": "Cunit*8",    # bit3
    "C6":  "Cunit*4",   "C9":  "Cunit*4",    # bit2
    "C7":  "Cunit*2",   "C8":  "Cunit*2",    # bit1
    # C15, C16 stay at Cunit*1 (bit0 LSB) — no change needed
}

modified = 0
for i, line in enumerate(lines):
    for cap_name, new_val in caps.items():
        # Match: "    C15 (net14 net15) capacitor c=OLD_VALUE"
        prefix = "    %s (" % cap_name  # e.g. "    C15 ("
        if line.startswith(prefix):
            # Find and replace the c= value
            import re
            old_line = line
            line = re.sub(r'c=Cunit\*\d+', 'c=' + new_val, line)
            if line != old_line:
                modified += 1
                break

with open(NETLIST, "w") as f:
    f.writelines(lines)

# Verify
print("Modified %d capacitors:" % modified)
for line in lines:
    if "capacitor c=" in line:
        print("  %s" % line.strip())
    if "ends TOP" in line:
        break

# Calculate total
total = 0
for line in lines:
    if "capacitor c=Cunit*" in line:
        val = int(line.split("Cunit*")[1].strip())
        total += val
print("\nTotal per side: %d Cu (should be 511)" % (total // 2))
