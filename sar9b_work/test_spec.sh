#!/bin/bash
# Test spectre with the EXACT Maestro command but from our directory
WD=/home/IC/Desktop/Project/SAR9B_400MV/netlist_sim
cd "$WD"

# Use absolute path for ahdllibdir
AHDL="$WD/sharedData/CDS/ahdl/input.ahdlSimDB"

# Use EXACT same flags as Maestro (except -format psfxl -> psfascii)
SPECTRE_DEFAULTS=-E \
/opt/eda/cadence/SPECTRE181/tools.lnx86/bin/spectre -64 input.scs \
    +escchars -format psfascii -raw raw_test \
    +aps +lqtimeout 900 -maxw 5 -maxn 5 \
    -ahdllibdir "$AHDL" \
    +logstatus > spectre_test.log 2>&1 &

PID=$!
echo "PID: $PID"
sleep 10
if ps -p $PID > /dev/null 2>&1; then
    echo "Still running..."
else
    echo "Finished. Errors:"
    grep -i error spectre_test.log | head -5
fi
