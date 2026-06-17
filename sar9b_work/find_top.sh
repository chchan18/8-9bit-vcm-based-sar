#!/bin/bash
cd /home/IC/Desktop/Project/SAR9B_400MV/netlist_sim
for f in ihnl/cds*/netlist; do
  if grep -q 'TOP_redun1_ADC' "$f" 2>/dev/null; then
    echo "=== $f ==="
    grep -n 'Cunit\|TOP_redun1_ADC\|capacitor c=' "$f" | head -30
    echo ""
  fi
done
