# TOP_redun1_ADC — 8-bit 400mV Redundancy SAR ADC

> **Data sources**: Schematic (`read_schematic`) + Spectre netlist (`input.scs`)  
> **Technology**: TSMC 28nm HPC+ (CRN28HPC+ v1.0)  
> **Supply**: 900mV (VDD), 450mV (Vcm)  
> **Input Range**: 800mVpp differential (Vpk=800m)  
> **Sampling Rate**: 400 MS/s (fs=400M)  
> **Resolution**: 8-bit (9-bit redundant CDAC → decoded to 8-bit)  
> **Measured Performance**: ENOB = 7.82 bits, SINAD = 48.84 dB  
> **Latest SAR9B_400MV 9-bit validation**: DAC9 `/out` ENOB = 7.86 bits, SINAD = 49.08 dB
> **Library**: `8BIT400MVcmredundancySAR`  
> **Simulator**: Spectre 18.1, `reltol=1e-3`, `errpreset=moderate`

---

## Architecture Overview

```
                          ┌─────────────────────────────────────────────────────┐
   CLKIN (400MHz) ───────►│              CLK_NOOVERLAP (I36)                     │
                          │    Non-overlapping clock generator                   │
                          │    → CLKON (sampling phase)                          │
                          │    → CLKOP (compare phase, drives BOOTSTRAP CLKS)    │
                          └──────┬──────────────────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
   ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
   │ BOOTSTRAP_DIFF   │  │  COMPARATOR  │  │ Asycontrol_logic │
   │ (I37)            │  │  (I0)        │  │ _9clk (I27)      │
   │ VIP/VIN→net7/net5│  │ net7=V-      │  │ 9-phase clock gen│
   │ Sampling Switch  │  │ net5=V+      │  │ Async SAR FSM    │
   └──────┬───────────┘  └──────┬───────┘  └────────┬─────────┘
          │                     │ VcompP/VcompN      │
          ▼                     ▼                    │
   ┌──────────────────┐  ┌──────────────┐     clki<8:0>
   │  CDAC Array      │  │ NOR2X1 (I29) │           │
   │  C0-C17 (9 pairs)│  │ → VALID_raw  │           │
   │  Top: net5/net7  │  └──────┬───────┘           │
   │  Bot: per-bit sw │         │                   │
   └──────┬───────────┘    ┌────┴────┐              │
          │                │ NAND2X1 │              │
          │  switch ctrl   │ (I28)   │              │
          ▼                │ EN·RAW  │              │
   ┌──────────────────────┐└────┬────┘              │
   │  control × 9 × 2     │    │                   │
   │  I1-I7,I16-I22,      │    ▼                   │
   │  I31-I32,I42-I43     │  VALID ────────────────┘
   │  (18 instances total)│
   └──────────┬───────────┘
              │
              ▼
       DOUTP<8:0> / DOUTN<8:0>  (9-bit differential redundant)
```

### Signal Flow

```
1. CLKIN ↑ → CLKON=1 → BOOTSTRAP samples VIP/VIN onto CDAC top plates (net5/net7)
2. CLKON ↓ → COMPARATOR strobes (CLKC), compares net5 vs net7
3. VcompP/VcompN → NOR → VALID_raw → NAND(EN) → VALID → advances shift register
4. clki<i> → control<i> switches CDAC bottom plates
5. Repeat 9× (MSB→LSB, non-binary weights with redundancy)
6. VALID=1 → 9-bit DOUTP/N ready
```

### Key Design Features

| Feature | Implementation | Benefit |
|---------|---------------|---------|
| **Redundancy** | 9-bit CDAC → 8-bit output | Error tolerance for metastability |
| **Non-binary weights** | 56/32/18/10/5/3/2/1/1 Cu | Digital error correction range |
| **Bootstrapped switch** | Constant-Vgs NMOS (cfmom_2t bootstrap caps) | Low distortion, high linearity |
| **Asynchronous SAR** | Self-timed 9-stage shift register | No high-speed clock needed after sampling |
| **StrongArm comparator** | Dynamic latch-based, 9 PMOS + 8 NMOS | Zero static power, fast decision |
| **Differential CDAC** | 9 pairs of MOM capacitors | Common-mode noise rejection |

---

## Standard Cell Library

All logic built from a minimal standard cell set (tsmcN28, L=30n unless noted):

| Cell | NMOS | PMOS | Drive | Schematic |
|------|------|------|-------|-----------|
| **INVX1** | 100n/30n, nf=1 | 200n/30n, nf=1 | 1× | Standard CMOS inverter |
| **INVX2** | 200n/30n, nf=1 | 400n/30n, nf=1 | 2× | Doubled drive |
| **INVX4** | 400n/30n, nf=1 | 800n/30n, nf=1 | 4× | Clock buffer |
| **INVX8** | 800n/30n, nf=2 | 1.6μ/30n, nf=2 | 8× | Final clock driver |
| **NAND2X1** | M0:100n, M3:100n, nf=1 | M1:200n, M2:200n, nf=1 | 1× | A·B → ZN |
| **NOR2X1** | M0:100n, M3:100n, nf=1 | M1:200n, M2:200n, nf=1 | 1× | A+B → ZN |
| **TRIGATEX1** | 100n/30n | 200n/30n | — | Transmission gate (OE/OEN) |
| **DELAY_1** | 100n/**100n**, nf=1 | 200n/**100n**, nf=1 | — | RC delay cell (L=100n for high R) |
| **OR3X1** | 4×400n/30n | 4×400n/30n | — | A+B+C → Z (NOR+INV) |
| **DFF** | Standard cell | — | — | D flip-flop (TRIGATEX1 master-slave) |
| **DFFRN** | DFF + NOR reset | — | — | DFF with active-low Reset (used in Asycontrol) |

### DELAY_1 Detail

The delay cell uses **L=100n** (not 30n) to increase channel resistance:

```
IN ──► INV (M0/M1) ──► net1 ──► INV (M4/M5) ──► Z
         NMOS 100n/100n         NMOS 100n/100n
         PMOS 200n/100n         PMOS 200n/100n
```

Long L increases Rout → RC delay with gate capacitance of next stage ≈ 50-100 ps.

### OR3X1 Schematic (NOR + INV)

```
A ─┬─ PMOS(400n) ─ VDD
B ─┤       ↓
C ─┘    net2 → net1 → Z
     ┌─────┘
A ─┬─┤
B ─┤ ├─ NMOS(400n) × 3 parallel → VSS
C ─┘
```

---

## Sub-Module Details

### 1. BOOTSTRAP_DIFF — Differential Bootstrapped Sampling Switch

**Cell**: `BOOTSTRAP_DIFF`  
**Instances**: 26 transistors + 2 MOM capacitors  
**Instance**: I37

#### Device List (from netlist)

**NMOS (14 devices)**:

| Device | W | L | multi | nf | Role |
|--------|---|---|-------|----|------|
| M9, M23 | 1μ | 30n | **2** | 1 | Main sampling switch (VIP→VOUTP, VIN→VOUTN) |
| M35, M34 | 1μ | 30n | **2** | 1 | Reset switches (VOUTP→VSS, VOUTN→VSS) |
| M24, M3 | 2μ | 30n | 1 | **2** | Bootstrap node discharge (CLKSB) |
| M0, M27 | 400n | 30n | 1 | 1 | Bootstrap cap precharge (CLKS) |
| M5, M32 | 400n | 30n | 1 | 1 | Clock buffer NMOS (CLKSB) |
| M4, M31 | 200n | 30n | 1 | 1 | Bootstrap node pull-down (VDD→PG/NG) |
| M8 | 500n | 30n | 1 | 1 | Bottom plate tracking |
| M7 | 210n | 30n | 1 | 1 | Bootstrap node pull-down path |
| M25, M26 | 500n/210n | 30n | 1 | 1 | N-side bottom plate tracking |

**PMOS (10 devices)**:

| Device | W | L | multi | nf | Role |
|--------|---|---|-------|----|------|
| M1, M28 | 800n | 30n | 1 | 1 | Bootstrap cap charger (CLKS) |
| M2, M30 | 2μ | 30n | 1 | **2** | Bootstrap cap charger (VDD→PG/NG) |
| M6, M29 | 500n | 30n | 1 | 1 | Bootstrap node pull-up |
| M12, M33 | 200n | 30n | 1 | 1 | Clock buffer PMOS (CLKSB) |

**Bootstrap Capacitors**:

| Device | Model | Dimensions | Est. Value |
|--------|-------|------------|------------|
| C0 | **cfmom_2t** | nr=70, lr=10μ, w=50n, s=50n, stm=1, spm=7 | ~443 fF |
| C2 | **cfmom_2t** | nr=70, lr=10μ, w=50n, s=50n, stm=1, spm=7 | ~443 fF |

> These are **MOM (Metal-Oxide-Metal) fringe capacitors**, not ideal caps — they include parasitics and process variation.

#### Operating Phases

```
CLKS=0, CLKSB=1 (Hold):
  M1/M28 OFF, M12/M33 ON → PG/NG pulled low
  M3/M24 ON → A/B discharged to VSS
  M9/M23 OFF → sampled charge held on CDAC

CLKS=1, CLKSB=0 (Sample):
  M1/M28 ON → C0/C2 top plates charged to VDD
  M0/M27 ON → bottom plates A/B track input through M8/M25
  PG/NG boosted to VDD + V(A/B) via capacitive coupling
  M9/M23 see Vgs ≈ VDD (constant) → linear sampling
```

#### Ports

| Port | Direction | Netlist Node | Description |
|------|-----------|-------------|-------------|
| VIP, VIN | Input | — | Differential analog input |
| VOUTP, VOUTN | Output | net7, net5 | Sampled output → CDAC top plates |
| CLKS | Input | CLKON | Sampling clock (from CLK_NOOVERLAP) |
| CLKSB | Input | — | Complement (generated internally) |
| VDD, VSS | Supply | — | 900mV, 0V |

---

### 2. CLK_NOOVERLAP — Non-Overlapping Clock Generator

**Cell**: `CLK_NOOVERLAP`  
**Instances**: I36 (14 gates)  
**Netlist**: `subckt CLK_NOOVERLAP CLKIN CLKON CLKOP VDD VSS`

#### Gate-Level Schematic

```
CLKIN ──► INVX1(I0)──┬──► TRIGATEX1(I15) ──► net11 (always on, OE=VDD,OEN=VSS)
                      │        │
                      │   ┌────┴──────────────────────────────┐
                      │   │  PATH A (CLKOP)                    │
                      │   │  NAND2(I10: A=net6, B=net11)       │
                      │   │  → DELAY_1(I12) → INVX1(I11)       │
                      │   │  → INVX4(I13) → INVX8(I17) → CLKON │
                      │   └───────────────────────────────────┘
                      │
                      └──► INVX1(I8)──► net10 ──► same TRIGATEX1
                           │
                      ┌────┴──────────────────────────────┐
                      │  PATH B (CLKON)                    │
                      │  INVX1(I2) → NAND2(I3: A=net3, B=net4) │
                      │  → DELAY_1(I5) → INVX1(I4)         │
                      │  → INVX4(I6) → INVX8(I16) → CLKOP  │
                      └───────────────────────────────────┘
                           ↑                              ↑
                           └── Cross-coupled feedback ────┘
```

#### Timing

```
CLKIN:   ──┐     ┌──────────────────
            └─────┘
CLKOP:   ──┐   ┌────────────────────  (sampling phase)
            └───┘
              │← Δt →│  non-overlap ≈ 2 × DELAY_1 ≈ 100-200 ps
CLKON:   ──────┐  ┌─────────────────  (compare phase)
                └──┘
```

| Port | Netlist | Description |
|------|---------|-------------|
| CLKIN | — | External clock (400 MHz) |
| CLKOP | → BOOTSTRAP.CLKS | Sampling clock |
| CLKON | → BOOTSTRAP.CLKSB | Compare clock |

---

### 3. COMPARATOR — StrongArm Latch Comparator

**Cell**: `COMPARATOR`  
**Instances**: I0 (17 transistors)  
**Netlist**: `subckt COMPARATOR CLKC VDD VN VON VOP VP VSS`

#### Device List (from netlist, all L=30n)

**PMOS (9 devices, all nf=2)**:

| Device | W | Connections (D G S B) | Role |
|--------|---|----------------------|------|
| M0 | 2μ | net2 CLKC VDD VDD | **Precharge switch** |
| M2 | 2μ | VAN VP net2 VDD | **Reference current source** (gate=VP) |
| M18 | 2μ | VAP VN net2 VDD | **Reference current source** (gate=VN) |
| M5 | 2μ | VAN1 VAP1 VDD VDD | **Reset/equalization** (gate=VAP1) |
| M8 | 2μ | VAN1 VAP VDD VDD | **Reset/equalization** (gate=VAP) |
| M9 | 2μ | VAP1 VAN1 VDD VDD | **Cross-coupled PMOS latch** (gate=VAN1) |
| M12 | 2μ | VAP1 VAN VDD VDD | **Cross-coupled PMOS latch** (gate=VAN) |
| M13 | 2μ | VON VAP1 VDD VDD | **Output pull-up** (gate=VAP1) |
| M15 | 2μ | VOP VAN1 VDD VDD | **Output pull-up** (gate=VAN1) |

**NMOS (8 devices, all nf=1)**:

| Device | W | Connections (D G S B) | Role |
|--------|---|----------------------|------|
| M1 | 1μ | VAP CLKC VSS VSS | **Tail switch** (gate=CLKC) |
| M3 | 1μ | VAN CLKC VSS VSS | **Tail switch** (gate=CLKC) |
| M6 | 1μ | net6 VAP1 VSS VSS | **Cross-coupled NMOS** (gate=VAP1) |
| M7 | 1μ | VAN1 VAP net6 VSS | **Cross-coupled NMOS** (gate=VAP) |
| M10 | 1μ | net8 VAN1 VSS VSS | **Cross-coupled NMOS** (gate=VAN1) |
| M11 | 1μ | VAP1 VAN net8 VSS | **Cross-coupled NMOS** (gate=VAN) |
| M14 | 1μ | VON VAP1 VSS VSS | **Output pull-down** (gate=VAP1) |
| M16 | 1μ | VOP VAN1 VSS VSS | **Output pull-down** (gate=VAN1) |

#### Core Operation

```
CLKC=1 (Reset):
  M0 precharges net2=VDD
  M2/M18 weakly pull VAP/VAN toward VDD
  M1/M3 discharge VAP/VAN to VSS through tail
  → VOP=VON≈VDD, VAP1=VAN1 reset

CLKC=0 (Evaluate):
  M1/M3 act as tail current sources
  M2/M18 differential pair: I(VN) vs I(VP) → asymmetric discharge
  M6/M7 + M10/M11 NMOS latch regenerates
  M9/M12 + M5/M8 PMOS latch reinforces
  → VOP/VON go rail-to-rail within ~100 ps
```

#### Key Measurements

| Metric | Value |
|--------|-------|
| Input pair W/L | 2μ/30n (PMOS) |
| Latch W/L | 1μ/30n (NMOS) |
| Precharge switch | 2μ/30n (PMOS) |
| Decision time | <100 ps (estimated) |
| Input CM range | ~200-700 mV (PMOS input) |

#### Ports

| Port | Netlist | Description |
|------|---------|-------------|
| VP, VN | net5, net7 | CDAC top-plate voltages |
| VOP, VON | VcompP, VcompN | Comparator outputs → NOR → VALID |
| CLKC | CLKC | Strobe clock (from Asycontrol) |

---

### 4. Asycontrol_logic_9clk — Asynchronous SAR Control

**Cell**: `Asycontrol_logic_9clk`  
**Instances**: I27 (9 × DFFRN + 1 × OR3X1)  
**Netlist**: `subckt Asycontrol_logic_9clk CLKC CLKO<8:0> CLKS VALID VDD VSS`

#### Shift Register Chain

```
CLKS (global reset) ──► RN of ALL DFFs

  I0 (DFFRN):  D=VDD    CLK=VALID  Q=CLKO<8> ──► control<8>
  I1 (DFFRN):  D=CLKO<8> CLK=VALID  Q=CLKO<7> ──► control<7>
  I2 (DFFRN):  D=CLKO<7> CLK=VALID  Q=CLKO<6> ──► control<6>
  I3 (DFFRN):  D=CLKO<6> CLK=VALID  Q=CLKO<5> ──► control<5>
  I4 (DFFRN):  D=CLKO<5> CLK=VALID  Q=CLKO<4> ──► control<4>
  I5 (DFFRN):  D=CLKO<4> CLK=VALID  Q=CLKO<3> ──► control<3>
  I6 (DFFRN):  D=CLKO<3> CLK=VALID  Q=CLKO<2> ──► control<2>
  I7 (DFFRN):  D=CLKO<2> CLK=VALID  Q=CLKO<1> ──► control<1>
  I11(DFFRN): D=CLKO<1> CLK=VALID  Q=CLKO<0> ──► control<0>

  CLKC = OR3X1(CLKS, VALID, CLKO<0>)
```

#### DFFRN (D Flip-Flop with active-low Reset)

Each DFFRN (10 gates):

```
D ──► TRIGATEX1 ×2 (master latch) ──► net2
    │                                  │
CLK─┼──► INVX2 → CLKP                  │
    │    INVX2 → CLKN                  ├──► TRIGATEX1 ×2 (slave latch) ──► Q
    │                                  │
RN ─┼──► INVX2 → R                     │
    └──► NOR2X1(R, slave_out)──► INVX1──► INVX4──► Q
```

#### Timing

```
CLKS:    ──┐                              ┌──  (start conversion pulse)
             └──────────────────────────────┘
CLKO<8>: ────┐    ┌────────────────────────────  (MSB, always 1)
               └────┘
CLKO<7>: ───────┐    ┌─────────────────────────
                  └────┘
CLKO<6>: ──────────┐    ┌──────────────────────
                     └────┘
  ...
CLKO<0>: ──────────────────────────────────────┐    ┌──
                                                  └────┘
VALID:   ───────────────────────────────────────────┐  ┌──
                                                       └──┘
CLKC:    ──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐  ┌──  (compare strobes)
             └─┘  └─┘  └─┘  └─┘  └─┘  └─┘  └─┘  └─┘  └─┘
             MSB                                      LSB  done
```

#### Ports

| Port | Direction | Description |
|------|-----------|-------------|
| CLKS | Input | Conversion start pulse |
| CLKC | Output | Comparator strobe |
| CLKO<8:0> | Output | Per-bit clocks to control cells |
| VALID | Input | Propagation trigger (feedback from NOR+NAND) |

---

### 5. control — Per-Bit CDAC Switch Cell

**Cell**: `control`  
**Instances**: 18 total (9 positive-side + 9 negative-side)  
**Netlist**: `subckt control Bi Vcm Vcomp VrefN VrefP cap clki`

#### Device List (from netlist)

| Device | Type | W | L | multi | nf | Gate | Source/Drain |
|--------|------|---|---|-------|----|------|--------------|
| M5 | NMOS | 800n | 30n | **2** | 1 | clkis | cap ↔ Vcm |
| M3 | NMOS | 800n | 30n | **2** | 1 | clki | net6 ↔ VrefN |
| M0 | NMOS | 800n | 30n | **2** | 1 | Bi | cap ↔ net6 (=VrefN path) |
| M4 | PMOS | 800n | 30n | **4** | 1 | clki | cap ↔ Vcm |
| M2 | PMOS | 800n | 30n | **4** | 1 | clkis | net12 ↔ VrefP |
| M1 | PMOS | 800n | 30n | **4** | 1 | Bi | cap ↔ net12 (=VrefP path) |
| I6 | INVX8 | — | — | — | — | clki → clkis | Clock inversion |
| I4 | DELAY_1 | — | — | — | — | Vcomp → net3 | Comparator delay |
| I5 | DFF | — | — | — | — | clki, net3 → Bi | Decision latch |

#### Switch States (per bit cycle)

```
Phase 1 (clki=1, clkis=0):
  M4 ON → cap pulled to Vcm through PMOS
  M2 ON → precharge path VrefP→net12

Phase 2 (Bi latched from Vcomp):
  If Bi=1: M1 ON → cap=VrefP (keep decision)
  If Bi=0: M0 ON → cap=VrefN (flip decision)
           → Also M5 (Vcm) provides intermediate recovery path

Note: VrefP=VDD=900mV, VrefN=VSS=0V, Vcm=450mV
```

#### Effective Switch Sizes

| Switch | Raw W | multi | Effective W |
|--------|-------|-------|-------------|
| PMOS (M1, M2, M4) | 800n | ×4 | **3.2μ** |
| NMOS (M0, M3, M5) | 800n | ×2 | **1.6μ** |

PMOS switches are **2× wider** than NMOS to compensate for lower mobility.

#### Ports

| Port | Direction | Description |
|------|-----------|-------------|
| clki | Input | Bit clock (from Asycontrol) |
| Vcomp | Input | Comparator decision |
| Bi | Output | Latched bit → DOUTP<i> or DOUTN<i> |
| cap | Bidirectional | CDAC bottom plate |
| VrefP, VrefN | Supply | 900mV / 0V |
| Vcm | Supply | 450mV |

---

### 6. CDAC Array — Redundant Capacitor DAC

**Components**: 18 MOM capacitors (9 differential pairs)  
**Type**: `capacitor` (ideal in schematic, Spectre `capacitor` model)  
**Unit**: `Cunit = 1f` (parameter)

#### Capacitor Weight Table

| Bit | Positive Cap | Negative Cap | Value | Node (P) | Node (N) | Binary Eq. | Overlap |
|-----|-------------|-------------|-------|----------|----------|------------|---------|
| 8 (MSB) | C2 | C17 | **56 Cu** | net5 | net7 | 128 | +28 |
| 7 | C0 | C14 | **32 Cu** | net5 | net7 | 64 | +4 |
| 6 | C1 | C13 | **18 Cu** | net5 | net7 | 32 | −10 |
| 5 | C4 | C11 | **10 Cu** | net5 | net7 | 16 | −10 |
| 4 | C3 | C12 | **5 Cu** | net5 | net7 | 8 | −3 |
| 3 | C5 | C10 | **3 Cu** | net5 | net7 | 4 | −1 |
| 2 | C6 | C9 | **2 Cu** | net5 | net7 | 2 | 0 |
| 1 | C7 | C8 | **1 Cu** | net5 | net7 | 1 | 0 |
| 0 | C15 | C16 | **1 Cu** | net5 | net7 | 1 | 0 |

**Total: 128 Cu** = 128 fF per side (with Cunit=1f)

#### Redundancy Check

```
sum(lower bits) for bit 8: 32+18+10+5+3+2+1+1 = 72 Cu > 56 Cu ✓ (MSB correctable)
sum(lower bits) for bit 7: 18+10+5+3+2+1+1 = 40 Cu > 32 Cu ✓
sum(lower bits) for bit 6: 10+5+3+2+1+1 = 22 Cu > 18 Cu ✓
sum(lower bits) for bit 5: 5+3+2+1+1 = 12 Cu > 10 Cu ✓
...
```

All bits satisfy `sum(lower) > weight(current)` → **full single-bit error correction**.

#### CDAC Topology

```
  net5 (top plate, connects to COMPARATOR.VP)
   │
   ├── C2  (56f) ─── I43.cap (DOUTP<8>)    ├── C17 (56f) ─── I42.cap (DOUTN<8>)
   ├── C0  (32f) ─── I1.cap  (DOUTP<7>)    ├── C14 (32f) ─── I16.cap (DOUTN<7>)
   ├── C1  (18f) ─── I2.cap  (DOUTP<6>)    ├── C13 (18f) ─── I17.cap (DOUTN<6>)
   ├── C4  (10f) ─── I3.cap  (DOUTP<5>)    ├── C11 (10f) ─── I18.cap (DOUTN<5>)
   ├── C3  (5f)  ─── I4.cap  (DOUTP<4>)    ├── C12 (5f)  ─── I19.cap (DOUTN<4>)
   ├── C5  (3f)  ─── I5.cap  (DOUTP<3>)    ├── C10 (3f)  ─── I20.cap (DOUTN<3>)
   ├── C6  (2f)  ─── I6.cap  (DOUTP<2>)    ├── C9  (2f)  ─── I21.cap (DOUTN<2>)
   ├── C7  (1f)  ─── I7.cap  (DOUTP<1>)    ├── C8  (1f)  ─── I22.cap (DOUTN<1>)
   ├── C15 (1f)  ─── I31.cap (DOUTP<0>)    ├── C16 (1f)  ─── I32.cap (DOUTN<0>)
   │
  net7 (top plate, connects to COMPARATOR.VN)
```

Both top plates are differential CDACs sampled to VIP/VIN by the bootstrap switch.

---

### 7. VALID Generation Logic

```
VcompP ──┬── NOR2X1(I29) ──► net6 (VALID_raw)
VcompN ──┘       │
                 ├──► NAND2X1(I28: A=net6, B=EN) ──► VALID
              EN ─┘
```

When comparator resolves (VcompP≠VcompN), VALID_raw goes high → VALID goes high (EN tied to VDD=always enabled) → triggers next bit in Asycontrol shift register.

---

## Testbench: ADC_redun1_tb

### Netlist Top-Level

```
parameters fs=400M Vpk=800m Cunit=1f Vth_sw=0.9 TSTOP=2.7u

V2 (clks VSS): pulse v1=0 v2=900m period=1/fs delay=1p rise=1p fall=1p 
               width=0.2/fs                          ← 20% duty cycle clock
V8 (VCM VSS): sine freq=(7/1024)*fs ampl=Vpk         ← coherent input 2.734 MHz
               sinedc=0 delay=50p
V3 (Vcm VSS): dc=450m                                ← ADC common-mode
V4 (EN VSS):  dc=900m                                ← enable always high
V0 (VDD VSS): dc=900m                                ← ADC supply
V1 (VSS 0):   dc=0                                   ← global ground
V6 (net12 VSS): dc=450m                              ← balun common-mode

I5 (VCM net12 VIP VIN): ideal_balun                  ← SE→Diff conversion
I0: TOP_redun1_ADC                                   ← DUT
I14: decode_redun9to8 (Verilog-A)                    ← 9b redundant → 8b
I15: DAC8b_va (Verilog-A)                             ← 8b → analog "out"
```

### Stimulus Summary

| Parameter | Value | Description |
|-----------|-------|-------------|
| `fs` | 400 MHz | Sampling rate |
| Clock duty | 20% (`width=0.2/fs`) | Pulse width |
| `fsig` | (7/1024)×fs ≈ **2.734 MHz** | Coherent input frequency |
| `Vpk` | 800 mV | Differential amplitude |
| `Vcm` | 450 mV | ADC common-mode |
| `TSTOP` | 2.7 μs | 1080 clock cycles |
| FFT Window | 26ns → 2.586μs | Skip startup, 1024-point FFT |
| `reltol` | 1e-3 | Moderate accuracy |
| `errpreset` | moderate | Spectre error tolerance |

### Output Chain

```
TOP_redun1_ADC ──► biP<8:0>/biN<8:0> (differential 9-bit)
                            │
                     decode_redun9to8 (Verilog-A)
                            │
                     8-bit bus D<7:0>
                            │
                       DAC8b_va (Verilog-A, N=8, VFS=0.9)
                            │
                          out (analog reconstructed)
                            │
                     FFT → ENOB, SINAD
```

### Simulator Configuration

```
simulatorOptions:
  reltol=1e-3, vabstol=1e-6, iabstol=1e-12
  temp=27, tnom=27
  gmin=1e-12, rforce=1

tran:
  stop=TSTOP (2.7μs)
  errpreset=moderate
  write="spectre.ic", writefinal="spectre.fc"
  annotate=status, maxiters=5

saveOptions: save=allpub
```

### Measured Results

| Metric | Value | Ideal | Loss |
|--------|-------|-------|------|
| **ENOB** | 7.819 bits | 8.0 bits | 0.18 bits |
| **SINAD** | 48.84 dB | 49.92 dB | 1.08 dB |
| **ENOB %** | 97.8% | 100% | 2.2% |

---

## 9-bit Binary CDAC Experiment (2026-06-16)

A follow-up experiment temporarily changed the `TOP_redun1_ADC` CDAC weights
from the redundant 128-Cu set to a binary 511-Cu set, then ran the same
`ADC_redun1_tb` Maestro setup through ADE Explorer.

The completed run is archived locally at:

```
sar9b_work/wave_exports_binary/ExplorerRun.0/
```

Captured active netlist evidence:

```
sar9b_work/wave_exports_binary/ExplorerRun.0/input.scs
```

Binary weights in that netlist:

| Bit | P cap | N cap | Weight |
|-----|-------|-------|--------|
| 8 | C2 | C17 | Cunit*256 |
| 7 | C0 | C14 | Cunit*128 |
| 6 | C1 | C13 | Cunit*64 |
| 5 | C4 | C11 | Cunit*32 |
| 4 | C3 | C12 | Cunit*16 |
| 3 | C5 | C10 | Cunit*8 |
| 2 | C6 | C9 | Cunit*4 |
| 1 | C7 | C8 | Cunit*2 |
| 0 | C15 | C16 | Cunit*1 |

Results using the existing decode/DAC8 path:

| Path | SINAD | ENOB | Note |
|------|-------|------|------|
| `decode_redun9to8` + `DAC8b_va` `/out` | 26.37 dB | 4.087 bits | Expected to be misleading for binary CDAC |
| Offline `/out` FFT from exported samples | 26.377 dB | 4.089 bits | Confirms offline FFT matches Maestro |

Raw 9-bit code was first reconstructed offline from saved internal DFF nodes.
Later checks showed that the top-level testbench nets are also exportable as
`VT("/biP<0>")` ... `VT("/biP<8>")`; these matched the inverse DFF-node mapping
with 0 mismatches across the 1024 sampled points. The validated fallback mapping is:

```
DOUTP0 = inverse of /I0/I31/I5/net7
DOUTP1 = inverse of /I0/I7/I5/net7
DOUTP2 = inverse of /I0/I6/I5/net7
DOUTP3 = inverse of /I0/I5/I5/net7
DOUTP4 = inverse of /I0/I4/I5/net7
DOUTP5 = inverse of /I0/I3/I5/net7
DOUTP6 = inverse of /I0/I2/I5/net7
DOUTP7 = inverse of /I0/I1/I5/net7
DOUTP8 = inverse of /I0/I43/I5/net7
```

Raw 9-bit offline result:

| Metric | Value |
|--------|-------|
| SINAD | 16.814 dB |
| ENOB | 2.501 bits |
| Code range | 10 to 503 |
| Code mean | 255.52 |

Follow-up netlist/Maestro logic checks:

| Path / check | Result |
|--------------|--------|
| DAC8 input nets `net18..net10` reconstructed offline | SINAD 26.338 dB, ENOB 4.083 bits |
| DAC8 input reconstruction vs `/out` | 0.138 mV rms error, 0.618 mV max error |
| Top-level `biP<*>` vs inverse DFF `net7` mapping | 0 mismatches |
| Direct binary raw code, best phase (`-900 ps` to `-300 ps`) | SINAD 29.160 dB, ENOB 4.551 bits |
| Direct binary raw code, default FFT grid (`0 ps`) | SINAD 16.814 dB, ENOB 2.501 bits |

Interpretation: the Maestro `/out` path is confirmed to be the old
`decode_redun9to8` + `DAC8b_va` path, while top-level raw `biP<8:0>` is now
validated for direct export. Sampling phase improves the raw binary result, but
does not restore high ENOB. The likely next experiment is to keep binary ratios
while reducing total CDAC load from 511 fF back near the original 128 fF, for
example by running the binary case with `Cunit=0.25f`.

### Scaled 9-bit Binary CDAC Result

The follow-up experiment kept the 9-bit binary ratios and reduced every binary
weight by 4x:

| Bit | P cap | N cap | Weight |
|-----|-------|-------|--------|
| 8 | C2 | C17 | Cunit*64 |
| 7 | C0 | C14 | Cunit*32 |
| 6 | C1 | C13 | Cunit*16 |
| 5 | C4 | C11 | Cunit*8 |
| 4 | C3 | C12 | Cunit*4 |
| 3 | C5 | C10 | Cunit*2 |
| 2 | C6 | C9 | Cunit*1 |
| 1 | C7 | C8 | Cunit*0.5 |
| 0 | C15 | C16 | Cunit*0.25 |

Per-side total is `127.75*Cunit`, close to the original 128 fF load with
`Cunit=1f`.

| Path / measurement | SINAD | ENOB | Note |
|--------------------|-------|------|------|
| Maestro legacy `/out` through `decode_redun9to8` + `DAC8b_va` | 23.18 dB | 3.558 bits | Still misleading for binary CDAC |
| Raw top-level `biP<8:0>`, +1200 ps offset | 43.936 dB | 7.006 bits | First sampled point above target |
| Raw top-level `biP<8:0>`, +1350 ps offset | 46.587 dB | 7.446 bits | Stable logic levels |
| Raw top-level `biP<8:0>`, +1500 to +2100 ps offset | 54.235 dB | 8.717 bits | Stable best plateau |

Run evidence:

| Item | Value |
|------|-------|
| Iteration folder | `sar9b_work/iterations/scaled_binary_q4/` |
| Spectre status | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 27m 49.0s |
| Code range at best phase | 24 to 487 |

Conclusion: the original full-size binary experiment was limited mainly by
CDAC load/switch settling. Once the binary CDAC total is brought back near the
original redundant CDAC load, raw-code ENOB exceeds the 7-bit target.

### Original-library 9-bit Maestro Validation Reference

A clean Maestro testbench was then created to avoid using the original
`ADC_redun1_tb` as the active design. This result is preserved as a reference,
but the active target has since moved to `SAR9B_400MV/ADC_9B_tb_best_q4`.

| Item | Value |
|------|-------|
| Maestro cell | `8BIT400MVcmredundancySAR/ADC_9B_tb_best_q4` |
| DUT | `I0 -> TOP_9B_BINARY` |
| CDAC weights | q4-scaled binary weights on `TOP_9B_BINARY` |
| History | `Interactive.1` |
| Spectre status | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 25m 44.6s |
| Maestro legacy `/out` | SINAD 16 dB, ENOB 2.365 bits |
| Raw `biP<8:0>` best | SINAD 49.451 dB, ENOB 7.922 bits |
| Best raw-code phase | `+1500 ps` |
| Stable high-ENOB window | `+1500 ps` through `+2250 ps` |

The captured netlist proves the true 9-bit DUT path:

```
I0 (...) TOP_9B_BINARY
```

The low Maestro `/out` value is due to the still-present legacy
`decode_redun9to8 -> DAC8b_va` output chain. The valid 9-bit metric is the
offline FFT of raw top-level `biP<8:0>`.

Artifacts:

```
sar9b_work/iterations/9bit_maestro_best_q4/
```

### SAR9B_400MV DAC9 Maestro Validation

The current validated 9-bit flow is in the dedicated `SAR9B_400MV` library.
The Maestro measurement chain was repaired so the active `/out` no longer uses
the old `decode_redun9to8 -> DAC8b_va` path. The testbench now measures the
9-bit raw code through a direct ideal DAC:

```
biP<0..8> -> DAC9b_va -> /out
```

Final run summary:

| Item | Value |
|------|-------|
| Library | `SAR9B_400MV` |
| Maestro cell | `ADC_9B_tb_best_q4` |
| DUT | `I0 -> SAR9B_400MV/TOP_9B_ADC` |
| CDAC weights | q4-scaled binary on `TOP_9B_ADC` |
| History | `Interactive.11` |
| Run time | 2026-06-17 14:32:29 -> 16:21:46 |
| Spectre status | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 1h 49m 18s |
| Maestro `/out` after DAC9 + p2200 repair | SINAD 49.08 dB, ENOB 7.86 bits |
| Raw `biP<8:0>` reference | SINAD 49.4385 dB, ENOB 7.9200 bits |

Captured `Interactive.11` netlist evidence:

```spectre
include "/home/IC/Desktop/Project/SAR9B_400MV/ADC_9B_tb_best_q4/maestro/sar9b_va_ahdl.scs"
I0 (...) TOP_9B_ADC
I15 (out VDD biP\<0\> biP\<1\> biP\<2\> biP\<3\> biP\<4\> biP\<5\> \
        biP\<6\> biP\<7\> biP\<8\>) DAC9b_va VFS=0.9 VTH=0.45 trise=1e-09 \
        tfall=1e-09 td=0 rout=1
```

The wrapper file contains only the DAC9 Verilog-A include:

```spectre
ahdl_include "/home/IC/Desktop/Project/SAR9B_400MV/DAC9b_va/veriloga/veriloga.va"
```

The final top-level netlist has no `decode_redun9to8`, no `DAC8b_va`, and no
empty `subckt DAC9b_va`. This fixes the old low-Maestro-ENOB failure mode
where the legacy 8-bit measurement path reported `ENOB=2.365`.

The default Maestro ENOB/SINAD outputs were also moved to the validated p2200
window for the finite-rise DAC9 `/out` waveform:

```skill
spectrumMeasurement(v("/out" ?result "tran") t 2.82e-08 2.5882e-06 1024 390600 2e+08 0 "Rectangular" 0 0 1 "enob")
spectrumMeasurement(v("/out" ?result "tran") t 2.82e-08 2.5882e-06 1024 390600 2e+08 0 "Rectangular" 0 0 1 "sinad")
```

`Interactive.11.log` reports:

```text
spectrum_enob_p2200  7.86
spectrum_sinad_p2200 49.08
spectrum_enob        7.86
spectrum_sinad       49.08
```

Artifacts:

```
sar9b_work/iterations/sar9b_maestro_best_q4/
sar9b_work/iterations/sar9b_maestro_best_q4/logs/Interactive.11.log
sar9b_work/iterations/sar9b_maestro_best_q4/maestro_files_loaded_phase_p2200/active.state
sar9b_work/iterations/sar9b_maestro_best_q4/measurement_chain_dac9_final_manifest.json
sar9b_work/iterations/sar9b_maestro_best_q4/phase_outputs_manifest.json
```

---

## Design Summary

| Attribute | Value |
|-----------|-------|
| Architecture | Differential asynchronous redundant SAR ADC |
| Technology | TSMC 28nm HPC+ (CRN28HPC+ v1.0) |
| Resolution | 8-bit (9-bit redundant internal) |
| Supply | 900 mV (VDD), 0V (VSS), 450mV (Vcm) |
| Input range | 800 mVpp differential |
| Sampling rate | 400 MS/s |
| Clock duty cycle | 20% |
| CDAC total | 128 fF per side (Cunit=1f) |
| CDAC type | 9 pairs non-binary weighted MOM caps |
| Comparator | StrongArm dynamic latch (17T: 9P + 8N) |
| Sampling | Differential bootstrapped (cfmom_2t caps) |
| SAR control | Asynchronous self-timed 9-phase shift register |
| Logic cells | 6 INV variants + NAND2 + NOR2 + TRIGATE + DELAY + OR3 + DFF + DFFRN |
| Transistor count | ~130 (ADC core, excluding decode + DAC) |
| ENOB (measured) | 7.82 bits @ 400MS/s |
| SINAD (measured) | 48.84 dB |
| SAR9B DAC9 `/out` ENOB | 7.86 bits @ 400MS/s |
| SAR9B DAC9 `/out` SINAD | 49.08 dB |
| Simulation | Spectre 18.1, reltol=1e-3, 24m 45s runtime |
| PDK | `/project_tsmcN28_NEW/.../CRN28HPCp/models/spectre/toplevel.scs`|

---

## File Inventory

| File | Location | Description |
|------|----------|-------------|
| Netlist | `versions/v003_ADC_documentation/input.scs` | Complete Spectre netlist (818 lines) |
| Schematic data | Bridge `read_schematic()` output | Structured hierarchy + params |
| Simulation log | Remote: `ExplorerRun.0.log` | Run summary with results |
| RDB | Remote: `ExplorerRun.0.rdb` | SQLite results database |
