#!/bin/bash
WD=/home/IC/Desktop/Project/SAR9B_400MV/netlist_sim
rm -rf "$WD"
mkdir -p "$WD"

SRC=/home/IC/simulation/8BIT400MVcmredundancySAR/ADC_redun1_tb/maestro/results/maestro/ExplorerRun.0

cp "$SRC/psf/Vcmbased_ADC_tb_1/netlist/input.scs" "$WD/"
cp -r "$SRC/psf/Vcmbased_ADC_tb_1/netlist/ihnl" "$WD/"
cp -r "$SRC/sharedData" "$WD/"

echo "Copied. Files:"
ls -la "$WD/"
echo "=== ihdl files ==="
ls "$WD/ihnl/"*/netlist 2>/dev/null
