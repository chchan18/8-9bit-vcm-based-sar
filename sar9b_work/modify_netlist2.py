#!/usr/bin/env python3
"""Modify TOP CDAC weights from redundant to binary using simple string replace."""
import sys

NETLIST = "/home/IC/Desktop/Project/SAR9B_400MV/netlist_sim/ihnl/cds16/netlist"

with open(NETLIST, "r") as f:
    content = f.read()

# Map: old_value -> new_value (applied in order, most specific first)
# Handle Cunit*1 carefully since it appears for 4 caps
replacements = [
    # First pass: unique values
    ("Cunit*56", "Cunit*256"),
    ("Cunit*32", "Cunit*128"),
    ("Cunit*18", "Cunit*64"),
    ("Cunit*10", "Cunit*32"),
    ("Cunit*5", "Cunit*16"),
    ("Cunit*3", "Cunit*8"),
    # Now Cunit*2 appears for C6, C9
    ("Cunit*2", "Cunit*4"),
    # Now Cunit*1 appears for C7, C8, C15, C16
    # We want C7,C8=Cunit*2 and C15,C16=Cunit*1
    # So change C7 and C8 first, then Cunit*1 stays for C15/C16
]

# First apply all value changes
for old, new in replacements:
    count = content.count(old)
    content = content.replace(old, new)
    if count > 0:
        print("  %s -> %s (%d occurrences)" % (old, new, count))

# Now fix C15 and C16 (bit 0 LSB) which were changed to Cunit*4 in the Cunit*1->2 step
# Wait, the replacements would turn Cunit*1 into Cunit*4 through the chain:
# Cunit*1 -> Cunit*2 (no, Cunit*1 wasn't in replacements)
# Actually Cunit*1 is NOT in replacements, so C15/C16 stay at Cunit*1. Good.
# But C7/C8 were at Cunit*1 originally, and we want them at Cunit*2.
# They won't be changed since Cunit*1 isn't in the replacement list.
# We need to handle C7/C8 separately.

# Let's use per-instance name replacement
with open(NETLIST, "r") as f:
    lines = f.readlines()

per_cap = {
    "C7":  "Cunit*2",
    "C8":  "Cunit*2",
}

for i, line in enumerate(lines):
    for cap_name, new_val in per_cap.items():
        prefix = "    %s (" % cap_name
        if line.startswith(prefix):
            # Find "c=OLD" and replace with "c=NEW"
            idx = line.find("capacitor c=")
            if idx > 0:
                old_val_start = idx + len("capacitor c=")
                old_val_end = line.find(" ", old_val_start)
                if old_val_end < 0:
                    old_val_end = len(line)
                old_part = line[old_val_start:old_val_end]
                lines[i] = line[:old_val_start] + new_val + line[old_val_end:]
                print("  %s: %s -> %s" % (cap_name, old_part.strip(), new_val))
                break

with open(NETLIST, "w") as f:
    f.writelines(lines)

# Verify
print("\nFinal capacitors:")
total = 0
with open(NETLIST) as f:
    for line in f:
        if "capacitor c=" in line:
            val_str = line.split("capacitor c=")[1].split()[0].strip()
            name = line.split("(")[0].strip()
            try:
                val = int(val_str.replace("Cunit*", ""))
                total += val
                print("  %s = %s" % (name, val_str))
            except:
                pass
        if "ends TOP" in line:
            break

print("\nTotal per side: %d Cu (should be 511)" % (total // 2))
