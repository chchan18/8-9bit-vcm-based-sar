# 8bitvcmvirtuoso — Project Status & Handoff

> **Date**: 2026-06-18
> **Session span**: Initial setup → SAR9B 9-bit Maestro validation → DAC9 `/out` ENOB measurement repair
> **Bridge**: IC@192.168.225.132 (Virtuoso IC618, Spectre 18.1, TSMC 28nm HPC+)

---

## 1. Environment

| Item | Value |
|------|-------|
| **Remote host** | 192.168.225.132 |
| **SSH user** | IC |
| **SSH auth** | Key-based (`~/.ssh/id_ed25519`, no passphrase) |
| **Virtuoso** | IC618 (`/opt/eda/cadence/IC618/`) |
| **Spectre** | 18.1 (`/opt/eda/cadence/SPECTRE181/bin/spectre`) |
| **PDK** | TSMC 28nm HPC+ (CRN28HPC+ v1.0_2p2) |
| **PDK path** | `/home/IC/Desktop/Project/project_tsmcN28_NEW/.../CRN28HPCp/models/spectre/` |
| **Python venv** | `E:\8bitvcmvirtuoso\.venv` (Python 3.12.7) |
| **Bridge CLI** | `virtuoso-bridge` (v0.7.0, installed editable from `virtuoso-bridge-lite/`) |
| **Bridge .env** | `~\.virtuoso-bridge\.env` (VB_REMOTE_HOST=192.168.225.132, VB_REMOTE_USER=IC) |

### Daemon status check
```bash
.venv\Scripts\virtuoso-bridge.exe status
```
If daemon shows "NO RESPONSE", reload in Virtuoso CIW:
```lisp
RBStopAll()
load("/tmp/virtuoso_bridge_IC/Chonghao_Chen/virtuoso_bridge/virtuoso_setup.il")
```

---

## 2. Directory Structure

```
E:\8bitvcmvirtuoso\
├── .claude/
│   ├── settings.json              # Project config: acceptEdits, SessionStart hook
│   ├── settings.local.json        # Personal overrides
│   └── skills/                    # NTFS Junctions to virtuoso-bridge-lite/skills/
│       ├── virtuoso/
│       ├── spectre/
│       └── optimizer/
├── .venv/                         # Python 3.12.7 + virtuoso-bridge v0.7.0
├── virtuoso-bridge-lite/          # Cloned from https://github.com/Arcadia-1/virtuoso-bridge-lite
├── logs/sessions/                 # Auto-created session log templates
├── versions/
│   ├── v001_initial-setup/        # Git, logging, hooks setup
│   ├── v002_virtuoso-bridge-lite/ # Bridge installation
│   ├── v003_ADC_documentation/    # ADC design README + netlist + input.scs
│   ├── v004_sar9b_dac9_measurement_chain/ # DAC9 measurement-chain repair docs
│   ├── v005_sar9b_vpk800_enob_recovery/   # Vpk=800m ENOB recovery docs
│   └── v006_sar9b_submodule_maestro/      # Standalone submodule Maestro TB docs
├── projects/
│   ├── sar9b_enob_recovery/       # SAR9B Vpk=800m recovery scripts and evidence
│   └── sar9b_submodule_maestro/   # Comparator/clock/control/bootstrap Maestro TBs
└── sar9b_work/                    # Working directory for 9-bit SAR development
    ├── *.py                       # Python scripts (TB fixes, netlist mods, sim runs)
    ├── *.sh                       # Shell scripts for remote execution
    └── netlist_standalone/        # Standalone netlist attempt (incomplete)
```

---

## 3. Libraries in Virtuoso

### 3.1 `8BIT400MVcmredundancySAR` (original, WORKING)

The original 8-bit redundant SAR ADC design.

| Cell | Type | Description |
|------|------|-------------|
| `TOP_redun1_ADC` | schematic+symbol | 9-bit redundant CDAC SAR ADC → decoded to 8-bit |
| `ADC_redun1_tb` | schematic+maestro | Testbench: coherent sampling, FFT → ENOB/SINAD |
| `TOP_9B_BINARY` | schematic+symbol | **Binary CDAC version** (256/128/64/32/16/8/4/2/1 = 511Cu) |
| `ADC_9B_tb_v2` | schematic (corrupted) | Attempted 9-bit TB — **DO NOT USE** |
| Standard cells | schematic | INVX1/2/4/8, NAND2X1, NOR2X1, TRIGATEX1, DELAY_1, OR3X1, DFF, DFFRN |
| Sub-blocks | schematic | BOOTSTRAP_DIFF, CLK_NOOVERLAP, COMPARATOR, Asycontrol_logic_9clk, control |
| `decode_redun9to8` | veriloga+symbol | 9-bit redundant → 8-bit (Verilog-A) |
| `DAC8b_va` | veriloga+symbol | 8-bit ideal DAC (Verilog-A) |

**Key result**: Maestro simulation of `ADC_redun1_tb` gives **ENOB=7.82 bits, SINAD=48.84 dB** (measured with original redundant weights).

### 3.2 `SAR9B_400MV` (new library, WORKING FOR 9-BIT VALIDATION)

Created for 9-bit ADC development. Contains copies of all sub-cells.

| Cell | Status | Description |
|------|--------|-------------|
| `TOP_9B_ADC` | ✅ schematic+symbol | 9-bit binary SAR ADC; active best run uses q4-scaled binary CDAC |
| `ADC_9B_tb_best_q4` | ✅ schematic+maestro | Current validated SAR9B Maestro testbench |
| `TB_SUBMOD_COMPARATOR_PERF` | ✅ schematic+maestro | Standalone comparator transient testbench |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | ✅ schematic+maestro | Standalone non-overlap clock transient testbench |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | ✅ schematic+maestro | Standalone 9-step asynchronous control transient testbench |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | ✅ schematic+maestro | Standalone differential bootstrap switch transient testbench |
| `ADC_9B_tb` | ❌ corrupted | Failed TB — DO NOT USE |
| All sub-cells | ✅ schematic | Copied from 8BIT400MVcmredundancySAR |
| VA cells | ✅ veriloga+symbol | `decode_redun9to8`, `DAC8b_va`, `DAC9b_va`; current Maestro wrapper includes `DAC9b_va` for the 9-bit `/out` measurement chain |
| `simulation/` | ✅ | Contains Verilog-A files and netlist attempt |

---

## 4. SKILL Bridge Capabilities (CRITICAL)

### What WORKS reliably:
- `execute_skill("expr")` — basic SKILL evaluation
- `inst~>c = "value"` — modifying instance parameters (capacitors, etc.)
- `dbOpenCellViewByType(... "r")` — opening cells in read mode
- `dbCopyCellView` — copying cells between libraries
- `dbGetInstByName(cv "name")` — reading instance properties
- `ddGetObj("lib" "cell")~>views~>name` — listing views
- Reading instance terminals and net connections
- `maeGetAnalysis`, `maeGetEnabledAnalysis` — reading Maestro config
- `open_gui_session` — opening Maestro GUI (WORKS but needs daemon)

### What DOES NOT WORK reliably:
- `schCreateInst` — **ALWAYS FAILS** (returns ERROR/empty)
- `schReplaceInst` — **FAILS** (returns ERROR)
- `dbOpenCellViewByType(... "a")` — **UNRELIABLE** (succeeds for some cells, fails for others due to locks)
- `dbCreateInst` — **FAILS**
- `schHiReplace` — returns nil, no matches found
- `run_and_wait` — fragile (SSH timeout issues, bridge disconnects)
- `close_gui_session` — can leave locked sessions

### Key insight:
**Modifying existing instance PARAMETERS works. Creating/deleting/replacing instances does NOT work through the bridge.** Design changes requiring instance manipulation must be done in the Virtuoso GUI.

---

## 5. PDK / Spectre Limitations

### Direct spectre invocation:
Spectre 18.1 CANNOT run the Maestro-generated `input.scs` directly because the PDK `toplevel.scs` uses `library tsmclib` which is only supported through Maestro's netlist pre-processor. All attempts to run spectre from command line fail with `SFE-675: Illegal library definition`.

### The `ihnl` / `blockdirmap` mechanism:
Maestro generates netlist fragments in `ihnl/cds*/netlist` directories with a `blockdirmap` index. These are auto-discovered by spectre when run through Maestro but NOT when run standalone.

### Workaround:
The ONLY way to run simulations with this PDK is through Maestro (either GUI or bridge API).

---

## 6. CDAC Weight Modification (PROVEN APPROACH)

This is the ONLY reliable way to change the ADC design through the bridge:

```python
# Works for TOP_redun1_ADC and TOP_9B_ADC
for cap_name, new_val in binary_weights.items():
    c.execute_skill(f'''
      let((cv inst)
        cv = dbOpenCellViewByType("{LIB}" "{CELL}" "schematic" "" "a")
        inst = dbGetInstByName(cv "{cap_name}")
        when(inst inst~>c = "{new_val}")
        dbSave(cv) dbClose(cv) t)
    ''', timeout=10)
```

### Binary weights (9-bit):
```
C2,C17: Cunit*256   (MSB)
C0,C14: Cunit*128
C1,C13: Cunit*64
C4,C11: Cunit*32
C5,C10: Cunit*8
C3,C12: Cunit*16
C6,C9:  Cunit*4
C7,C8:  Cunit*2
C15,C16: Cunit*1   (LSB)
Total: 511 Cu per side
```

### Original redundant weights (8-bit decoded):
```
C2,C17: Cunit*56    C1,C13: Cunit*18    C6,C9:  Cunit*2
C0,C14: Cunit*32    C4,C11: Cunit*10    C7,C8:  Cunit*1
                    C3,C12: Cunit*5     C15,C16: Cunit*1
                    C5,C10: Cunit*3
Total: 128 Cu per side
```

---

## 7. Simulation Results

### 8-bit Redundant (original): `ADC_redun1_tb`
| Metric | Value |
|--------|-------|
| ENOB | 7.82 bits |
| SINAD | 48.84 dB |
| Runtime | ~25 min |
| Date | 2026-06-16 |

### 9-bit Binary (modified CDAC only): `ADC_redun1_tb` with binary TOP
| Metric | Value |
|--------|-------|
| ENOB | 4.09 bits |
| SINAD | 26.37 dB |
| Runtime | ~25 min |
| Date | 2026-06-16 |
| ⚠️ Caveat | Measurement through `decode_redun9to8` chain — ENOB artificially low due to decode mismatch |

### 9-bit Binary raw-code measurement (latest handoff update)

Run completed through Maestro/ADE Explorer with binary CDAC weights verified in the active netlist:

| Item | Value |
|------|-------|
| Run history | `ExplorerRun.0` |
| Start → end | 2026-06-16 23:14:07 → 23:51:09 |
| Spectre status | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 36m 49.9s |
| Active netlist evidence | `sar9b_work/wave_exports_binary/ExplorerRun.0/input.scs` |
| Offline waveform exports | `sar9b_work/wave_exports_binary/ExplorerRun.0/` |

The binary weights in the captured netlist are:

```
C2,C17: Cunit*256
C0,C14: Cunit*128
C1,C13: Cunit*64
C4,C11: Cunit*32
C3,C12: Cunit*16
C5,C10: Cunit*8
C6,C9:  Cunit*4
C7,C8:  Cunit*2
C15,C16: Cunit*1
```

Offline measurement used the same FFT window as the Maestro outputs:

```
start = 26 ns
stop  = 2.586 us
N     = 1024
fundamental bin = 7
```

Results:

| Measurement path | SINAD | ENOB | Notes |
|------------------|-------|------|-------|
| Existing `/out` through `decode_redun9to8` + `DAC8b_va` | 26.377 dB | 4.089 bits | Matches Maestro log (`26.37 dB`, `4.087 bits`), validates the offline FFT script |
| Raw `DOUTP<8:0>` reconstructed offline | 16.814 dB | 2.501 bits | Uses saved internal DFF nodes because top-level `DOUTP<*>` nets are not saved directly |

Raw-bit reconstruction details:

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

The direct raw 9-bit result is much worse than the original redundant decode result. Treat it as a real measurement of the current binary-weight/raw-DOUTP configuration, but verify bit mapping and sample phase before making architectural conclusions.

### 9-bit Binary raw-code validation update (2026-06-17)

Additional netlist/Maestro logic checks were performed without rerunning Spectre:

| Check | Result | Evidence |
|-------|--------|----------|
| Maestro `/out` chain | `I0(TOP_redun1_ADC)` → `I14(decode_redun9to8)` → `I15(DAC8b_va)` | Captured netlist lines 783-792 |
| DAC8 input reconstruction | `DAC_B0..7` gives `SINAD=26.338 dB`, `ENOB=4.083 bits` | Matches `/out` within `0.138 mV rms`, `0.618 mV max` |
| Top-level raw bits | `VT("/biP<0>")` ... `VT("/biP<8>")` export successfully | No need to rely only on internal DFF nodes |
| Internal DFF mapping | Inverse `/I0/<control>/I5/net7` exactly matches top-level `biP<*>` at the sampled points | 0 mismatches on all 9 bits |
| Direct binary sample phase | Best tested phase is `-900 ps` to `-300 ps` relative to Maestro FFT grid | `SINAD=29.160 dB`, `ENOB=4.551 bits`, code range `20..491` |
| Default FFT grid raw binary | `0 ps` offset remains poor | `SINAD=16.814 dB`, `ENOB=2.501 bits`, code range `10..503` |

Artifacts:

| File | Content |
|------|---------|
| `sar9b_work/analyze_dout_logic.py` | Local analysis of `/out`, decoder outputs, top-level `biP`, and internal DFF node mapping |
| `sar9b_work/export_decoder_nodes.py` | Exports `DAC_B0..7` and `biP<0..8>` from an existing Maestro history |
| `sar9b_work/export_bip_phase_sweep.py` | Direct-PSF phase sweep of top-level `biP<8:0>` without opening/closing ADE GUI |
| `sar9b_work/wave_exports_binary/ExplorerRun.0/dout_logic_analysis.json` | Decoder/DAC/BIP mapping results |
| `sar9b_work/wave_exports_binary/ExplorerRun.0/phase_sweep/bip_phase_sweep.json` | Raw binary phase sweep results |

Interpretation:

1. The raw bit mapping is now validated: top-level `biP<*>` is exportable and matches the earlier inverse-DFF reconstruction exactly.
2. Sampling phase matters. The original `26 ns + k/fs` grid catches the direct binary output at a poor point; sampling about `0.3 ns` to `0.9 ns` earlier improves raw binary ENOB from `2.50` to `4.55` bits.
3. The remaining loss is not explained by bit order, polarity, or basic sample phase. The strongest current hypothesis is that the binary CDAC change increased total CDAC load from `128 fF` to `511 fF` per side while leaving the original switch sizing and asynchronous timing unchanged.
4. Next simulation experiment: keep binary ratios but reduce total capacitance near the original load, e.g. set `Cunit=0.25f` for the binary-weight run (or equivalently scale all binary cap values by 1/4), then export `biP<8:0>` with the `-900 ps` phase window.

### Iteration result: scaled 9-bit binary CDAC reaches target (2026-06-17)

The next experiment kept binary ratios but scaled the total CDAC load down by
4x so the per-side total is close to the original redundant design:

| Bit | P cap | N cap | Weight |
|-----|-------|-------|--------|
| 8 | C2 | C17 | `Cunit*64` |
| 7 | C0 | C14 | `Cunit*32` |
| 6 | C1 | C13 | `Cunit*16` |
| 5 | C4 | C11 | `Cunit*8` |
| 4 | C3 | C12 | `Cunit*4` |
| 3 | C5 | C10 | `Cunit*2` |
| 2 | C6 | C9 | `Cunit*1` |
| 1 | C7 | C8 | `Cunit*0.5` |
| 0 | C15 | C16 | `Cunit*0.25` |

Per-side total: `127.75*Cunit` with `Cunit=1f`.

| Item | Value |
|------|-------|
| Iteration label | `scaled_binary_q4` |
| Run history | `ExplorerRun.0` |
| Run time | 2026-06-17 00:58:53 → 01:26:54 |
| Spectre result | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 27m 49.0s |
| Maestro legacy `/out` result | SINAD 23.18 dB, ENOB 3.558 bits |
| Raw top-level `biP<8:0>` best result | SINAD 54.235 dB, ENOB 8.717 bits |
| Best raw-code sample phase | `+1500 ps` relative to the original Maestro FFT grid |
| Stable high-ENOB window | `+1500 ps` through `+2100 ps` all gave ENOB 8.717 bits |
| First phase above 7-bit target | `+1200 ps`: SINAD 43.936 dB, ENOB 7.006 bits |
| Best code range | 24 to 487 |

Artifacts:

| File | Content |
|------|---------|
| `sar9b_work/iterations/scaled_binary_q4/README.md` | Iteration summary |
| `sar9b_work/iterations/scaled_binary_q4/input.scs` | Captured Maestro netlist proving scaled weights |
| `sar9b_work/iterations/scaled_binary_q4/logs/ExplorerRun.0.log` | Maestro run log |
| `sar9b_work/iterations/scaled_binary_q4/logs/spectre.out` | Spectre log |
| `sar9b_work/iterations/scaled_binary_q4/phase_sweep_fine/bip_phase_sweep.json` | Validated raw-code phase sweep |

Interpretation: the full-size binary CDAC (`511 fF` per side) was primarily
limited by CDAC/switch settling and load, not by raw-bit mapping or polarity.
Keeping binary ratios while reducing the total CDAC load near the original
`128 fF` per side restores enough settling margin to exceed the 7-bit target.
After this run, `sar9b_work/restore.py` was executed successfully and restored
all 18 CDAC capacitors to their original redundant weights.

### Original-library 9-bit Maestro validation update (2026-06-17, superseded)

The previous q4 result was obtained by temporarily modifying the 8-bit
`ADC_redun1_tb` DUT path. A clean real 9-bit Maestro testbench was therefore
created and run in the original library. This result is preserved as a
reference, but the requested active target is now the `SAR9B_400MV` run in the
next section.

| Item | Value |
|------|-------|
| Library | `8BIT400MVcmredundancySAR` |
| Maestro cell | `ADC_9B_tb_best_q4` |
| DUT instance | `I0 -> TOP_9B_BINARY` |
| CDAC weights | q4-scaled binary weights on `TOP_9B_BINARY` |
| History | `Interactive.1` |
| Run time | 2026-06-17 09:16:56 -> 09:42:42 |
| Spectre result | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 25m 44.6s |
| Maestro legacy `/out` result | SINAD 16 dB, ENOB 2.365 bits |
| Raw top-level `biP<8:0>` best result | SINAD 49.451 dB, ENOB 7.922 bits |
| Best raw-code sample phase | `+1500 ps` relative to the original Maestro FFT grid |
| Stable high-ENOB window | `+1500 ps` through `+2250 ps` all gave ENOB 7.922 bits |
| Best code range | 125 to 386 |

The netlist for `Interactive.1` explicitly contains:

```
I0 (...) TOP_9B_BINARY
```

and the `TOP_9B_BINARY` subckt contains the q4 weights:

```
C2,C17:   Cunit*64
C0,C14:   Cunit*32
C1,C13:   Cunit*16
C4,C11:   Cunit*8
C3,C12:   Cunit*4
C5,C10:   Cunit*2
C6,C9:    Cunit*1
C7,C8:    Cunit*0.5
C15,C16:  Cunit*0.25
```

The legacy Maestro `/out` value is still low because this repaired testbench
keeps the old `decode_redun9to8 -> DAC8b_va` measurement chain. The valid
9-bit metric is the raw `biP<8:0>` offline FFT from the same PSF result.

Artifacts:

| File | Content |
|------|---------|
| `sar9b_work/iterations/9bit_maestro_best_q4/README.md` | Real 9-bit Maestro run summary |
| `sar9b_work/iterations/9bit_maestro_best_q4/run_complete_manifest.json` | Final run paths and key metrics |
| `sar9b_work/iterations/9bit_maestro_best_q4/input.scs` | Captured netlist proving `TOP_9B_BINARY` and q4 weights |
| `sar9b_work/iterations/9bit_maestro_best_q4/logs/Interactive.1.log` | Maestro run log |
| `sar9b_work/iterations/9bit_maestro_best_q4/logs/spectre.out` | Spectre log |
| `sar9b_work/iterations/9bit_maestro_best_q4/phase_sweep/bip_phase_sweep.json` | Broad raw-code phase sweep |
| `sar9b_work/iterations/9bit_maestro_best_q4/phase_sweep_fine/bip_phase_sweep.json` | Fine raw-code phase sweep |

### SAR9B_400MV 9-bit Maestro validation update (2026-06-17, current)

The requested SAR9B library/cell was repaired and run directly. The latest
update also fixes the Maestro `/out` measurement chain: the old
`decode_redun9to8 -> DAC8b_va` path has been removed from the active SAR9B
testbench and replaced by a direct `biP<0..8> -> DAC9b_va -> /out` path.

| Item | Value |
|------|-------|
| Library | `SAR9B_400MV` |
| Maestro cell | `ADC_9B_tb_best_q4` |
| DUT instance | `I0 -> SAR9B_400MV/TOP_9B_ADC` |
| CDAC weights | q4-scaled binary weights on `TOP_9B_ADC` |
| Verilog-A include method | `ADC_9B_tb_best_q4/maestro/sar9b_va_ahdl.scs` wrapper, containing only `DAC9b_va` |
| History | `Interactive.11` |
| Run time | 2026-06-17 14:32:29 -> 16:21:46 |
| Spectre result | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 1h 49m 18s |
| Maestro `/out` result after DAC9 chain + p2200 FFT repair | SINAD 49.08 dB, ENOB 7.86 bits |
| Raw top-level `biP<8:0>` best result from repaired SAR9B PSF | SINAD 49.4385 dB, ENOB 7.9200 bits |
| Best raw-code sample phase | `+1500 ps` relative to the original Maestro FFT grid |
| `/out` DAC waveform FFT window | `+2200 ps`, i.e. `28.2 ns -> 2.5882 us`, gives ENOB 7.86 bits |
| Best code range | 125 to 386 |

Netlist evidence from `Interactive.11`:

```spectre
include "/home/IC/Desktop/Project/SAR9B_400MV/ADC_9B_tb_best_q4/maestro/sar9b_va_ahdl.scs"
I0 (...) TOP_9B_ADC
I15 (out VDD biP\<0\> biP\<1\> biP\<2\> biP\<3\> biP\<4\> biP\<5\> \
        biP\<6\> biP\<7\> biP\<8\>) DAC9b_va VFS=0.9 VTH=0.45 trise=1e-09 \
        tfall=1e-09 td=0 rout=1
```

The wrapper contains:

```spectre
ahdl_include "/home/IC/Desktop/Project/SAR9B_400MV/DAC9b_va/veriloga/veriloga.va"
```

The captured top-level netlist has no `decode_redun9to8`, no `DAC8b_va`, and
no empty `subckt DAC9b_va`. The old `ENOB=2.365` failure mode is therefore
fixed. `Interactive.10` first proved the DAC9 chain was structurally correct
but still used the original Maestro FFT grid, giving `/out` ENOB 3.56 bits.
The final setup changes the default `spectrum_enob` and `spectrum_sinad`
expressions to the validated p2200 `/out` window:

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

| File | Content |
|------|---------|
| `sar9b_work/iterations/sar9b_maestro_best_q4/README.md` | Current SAR9B run summary |
| `sar9b_work/iterations/sar9b_maestro_best_q4/run_complete_manifest.json` | Final remote paths and Spectre summary |
| `sar9b_work/iterations/sar9b_maestro_best_q4/input.scs` | Captured SAR9B `Interactive.11` netlist proving wrapper, DUT, q4 weights, and `DAC9b_va` `/out` chain |
| `sar9b_work/iterations/sar9b_maestro_best_q4/sar9b_va_ahdl.scs` | Local copy of the AHDL wrapper |
| `sar9b_work/iterations/sar9b_maestro_best_q4/logs/Interactive.11.log` | Final Maestro run log with p2200 `/out` ENOB 7.86 bits |
| `sar9b_work/iterations/sar9b_maestro_best_q4/logs/spectre.out` | Spectre log |
| `sar9b_work/iterations/sar9b_maestro_best_q4/phase_sweep/bip_phase_sweep.json` | Broad raw-code phase sweep |
| `sar9b_work/iterations/sar9b_maestro_best_q4/phase_sweep_fine/bip_phase_sweep.json` | Fine raw-code phase sweep |
| `sar9b_work/iterations/sar9b_maestro_best_q4/phase_sweep_interactive10/bip_phase_sweep.json` | Raw-code phase sweep from the repaired `Interactive.10` run |
| `sar9b_work/iterations/sar9b_maestro_best_q4/out_phase_interactive10_fine/out_phase_sweep.json` | `/out` phase sweep selecting p2200 window |
| `sar9b_work/iterations/sar9b_maestro_best_q4/maestro_files_loaded_phase_p2200/active.state` | Verified Maestro setup with corrected default `spectrum_enob/sinad` expressions |

### SAR9B_400MV Vpk=800m ENOB recovery update (2026-06-17, current best)

The new `projects/sar9b_enob_recovery/` investigation confirmed that the
previous `Interactive.11` ENOB `7.86` result was dominated by a hidden Maestro
variable override: the generated netlist used `Vpk=450m`, while the intended
high-ENOB setup uses `Vpk=800m`.

A pure Maestro XML upload was not enough because an already-open ADE session
could write stale `Vpk=450m` values back into `maestro.sdb`. The successful
run therefore set `Vpk=800m` directly in the live Maestro session, saved the
setup, started the run, and verified the generated netlist before measuring.

| Item | Value |
|------|-------|
| Project | `projects/sar9b_enob_recovery` |
| Library | `SAR9B_400MV` |
| Maestro cell | `ADC_9B_tb_best_q4` |
| History | `Interactive.12` |
| Netlist Vpk evidence | `parameters fs=400M Vpk=800m Cunit=1f Vth_sw=0.9 TSTOP=2.7u` |
| Spectre result | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 36m 58.5s |
| Maestro default `/out` outputs | SINAD 54.01 dB, ENOB 8.678 bits |
| Raw top-level `biP<8:0>` best result | SINAD 54.2559 dB, ENOB 8.7203 bits |
| Best raw-code sample phase | `+1500 ps` relative to the original Maestro FFT grid |
| Raw code range | 24 to 487 |
| DAC9 `/out` phase-sweep best result | SINAD 54.1370 dB, ENOB 8.7005 bits |
| Best DAC9 `/out` sample phase | `+2250 ps` relative to the original Maestro FFT grid |
| DAC9 `/out` range | 42.27 mV to 857.73 mV |

Artifacts:

| File | Content |
|------|---------|
| `projects/sar9b_enob_recovery/README.md` | Root-cause project summary and final recovery result |
| `projects/sar9b_enob_recovery/analysis/2026-06-17_root_cause.md` | Root-cause calculations plus verification run |
| `projects/sar9b_enob_recovery/scripts/start_vpk800_maestro_run.py` | Live-session `Vpk=800m` setter, runner, and netlist verifier |
| `projects/sar9b_enob_recovery/scripts/check_vpk800_run.py` | Run polling and log/netlist archiver |
| `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/run_start_manifest.json` | Interactive.12 setup and netlist-verification manifest |
| `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/run_complete_manifest.json` | Spectre completion manifest |
| `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/input.scs` | Captured `Vpk=800m` netlist |
| `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/logs/Interactive.12.log` | Maestro run log with `Vpk 800m` |
| `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/logs/spectre.out` | Spectre log |
| `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/phase_sweep_bip/bip_phase_sweep.json` | Raw `biP<8:0>` phase sweep |
| `projects/sar9b_enob_recovery/runs/vpk800_p2200_baseline/out_phase_sweep/out_phase_sweep.json` | DAC9 `/out` phase sweep |

Interpretation: the active SAR9B 9-bit path and the repaired
`biP<0..8> -> DAC9b_va -> /out` measurement chain are now both validated near
`8.7` ENOB at nominal. Remaining work should focus on robustness sweeps rather
than basic measurement-chain repair.

---

## 8. Remaining Tasks

### New Project: SAR9B ENOB recovery

A new investigation project has been opened at
`projects/sar9b_enob_recovery/`.

Root-cause result: the previous `SAR9B_400MV` ENOB `7.86` value was low mostly
because the final Maestro netlist used `Vpk=450m`, while the intended q4 setup
uses `Vpk=800m`. A live-session `maeSetVar` flow forced the correct variable
precedence, generated an `Interactive.12` netlist with `Vpk=800m`, and
recovered:

| Path | SINAD | ENOB | Best phase |
|------|-------|------|------------|
| Raw `biP<8:0>` | 54.2559 dB | 8.7203 bits | `+1500 ps` |
| Maestro default `/out` | 54.01 dB | 8.678 bits | p2200 output expression |
| DAC9 `/out` phase-sweep best | 54.1370 dB | 8.7005 bits | `+2250 ps` |

The first project artifact,
`projects/sar9b_enob_recovery/artifacts/maestro_files_vpk800_p2200/`, remains
useful as a patched setup backup, but the robust operational flow is
`scripts/start_vpk800_maestro_run.py`, which sets variables in the live Maestro
session and verifies the generated netlist.

### New Project: SAR9B submodule Maestro testbenches

A submodule validation project has been opened at
`projects/sar9b_submodule_maestro/`.

Created in `SAR9B_400MV`:

| Testbench | DUT | Metric target |
|-----------|-----|---------------|
| `TB_SUBMOD_COMPARATOR_PERF` | `COMPARATOR` | Decision delay and output swing |
| `TB_SUBMOD_CLK_NOOVERLAP_PERF` | `CLK_NOOVERLAP` | Non-overlap timing |
| `TB_SUBMOD_ASYCTRL_9CLK_PERF` | `Asycontrol_logic_9clk` | 9-step SAR clock sequencing |
| `TB_SUBMOD_BOOTSTRAP_DIFF_PERF` | `BOOTSTRAP_DIFF` | Sampling switch tracking |

Status:

1. Done: symbol/source inspection, schematic testbench creation, and Maestro
   `TRAN` setup for all four cells.
2. Done: bridge-created schematic extraction metadata repaired with
   `dbSetConnCurrent` after initial netlisting failed with `OSSHNL-108` and
   `OSSHNL-109`.
3. Done: generated testbenches rebuilt with a real `VSS_SRC (VSS 0)` ground
   reference through `analogLib/gnd`; plain `"0"` labels produced floating
   `_net0` references.
4. Done: all four rebuilt Maestro testbenches now run through ADE/Maestro and
   Spectre with zero errors: comparator `Interactive.0`, clock non-overlap
   `Interactive.0`, ASYCTRL `Interactive.0`, and bootstrap `Interactive.0`.
5. Done: ASYCTRL standalone stimulus now exercises the full 9-step sequence.
   `DFFRN.RN` is active-high in this implementation, so `CLKS` is held high
   only for startup reset and then kept low while `VALID` pulses advance the
   chain. In `Interactive.0`, all nine `CLKO<0..8>` outputs reach rail; first
   rises progress from `CLKO<8>` at `542 ps` to `CLKO<0>` at `20543 ps`.
6. Done: online metric references were mapped into Maestro point outputs for
   comparator delay/swing, non-overlap timing, ASYCTRL sequence timing/rail
   reach, and bootstrap tracking/settling error. The run helper also records
   `maestro_metrics` from the ADE log.
7. Done: supply power and energy are still tracked, but as offline PSF metrics
   computed from `getData("/VDD_SRC/PLUS" ?result "tran")`, because IC618
   Maestro point outputs reject branch-current expressions as `Error No`.
8. Remaining: add robustness sweeps for ASYCTRL `VALID` spacing, comparator
   input overdrive, non-overlap timing, and bootstrap tracking across corners.

### Priority 1: Proper 9-bit measurement
Raw-code measurement was first completed without editing the schematic:

1. Binary CDAC weights were applied to `TOP_redun1_ADC`.
2. Maestro/ADE Explorer was run through the GUI `Update and Run` path.
3. The active binary netlist was captured locally.
4. `/out` and the 9 raw DOUTP-equivalent internal DFF nodes were exported at the 1024 FFT sample points.
5. Offline FFT produced raw-code `ENOB=2.501 bits`, `SINAD=16.814 dB`.
6. CDAC weights were restored to the original redundant values and verified.

Target-achieved validation work:

1. Done: `SAR9B_400MV/ADC_9B_tb_best_q4` was repaired and run through
   Maestro as history `Interactive.5`, then rerun as `Interactive.10` after
   the `/out` measurement chain repair, and finally rerun as `Interactive.11`
   after the p2200 Maestro output-expression repair.
2. Done: `I0` points to `SAR9B_400MV/TOP_9B_ADC`; TOP internals point to
   SAR9B cells; q4-scaled binary weights are in the captured netlist.
3. Done: raw `biP<8:0>` measurement from the SAR9B Maestro PSF gives
   `ENOB=7.9200 bits`, `SINAD=49.4385 dB` at `+1500 ps` in the repaired
   `Interactive.10` run.
4. Done: legacy `decode_redun9to8 -> DAC8b_va` `/out` path was replaced with
   direct `biP<0..8> -> DAC9b_va -> /out`; `Interactive.11` netlist proves no
   `decode_redun9to8`, no `DAC8b_va`, and no empty `DAC9b_va` subckt.
5. Done: Maestro default `spectrum_enob` and `spectrum_sinad` now use the
   p2200 `/out` FFT window (`28.2 ns -> 2.5882 us`, 1024 samples), and
   `Interactive.11` reports `ENOB=7.86 bits`, `SINAD=49.08 dB`.
6. Done: `Interactive.12` forced the intended `Vpk=800m` live Maestro setup
   and recovered raw `biP<8:0>` ENOB `8.7203 bits`, Maestro default `/out`
   ENOB `8.678 bits`, and DAC9 `/out` phase-sweep ENOB `8.7005 bits`.
7. Sweep PVT/input amplitude and confirm the high-ENOB plateau is robust.
7. Decide whether fractional `Cunit*0.5` and `Cunit*0.25` values are acceptable
   physically, or replace them with an explicit smaller `Cunit` and integer
   binary weights.

### Priority 2: Standalone netlist
Investigate if Spectre 19+ or `-lib` flag can bypass the PDK `library` statement issue.

### Priority 3: Documentation
- Done: `versions/v003_ADC_documentation/README_TOP_redun1_ADC.md` now includes
  the final `SAR9B_400MV/ADC_9B_tb_best_q4` DAC9 `/out` result
  (`ENOB=7.86 bits`, `SINAD=49.08 dB`) and raw-code reference
  (`ENOB=7.9200 bits`, `SINAD=49.4385 dB`).

---

## 9. Quick Reference Commands

### Check bridge status
```powershell
.venv\Scripts\virtuoso-bridge.exe status
```

### Run Python script through bridge
```powershell
.venv\Scripts\python.exe sar9b_work\script_name.py
```

### Check simulation results via SSH
```powershell
ssh IC@192.168.225.132 'cat /home/IC/Desktop/Project/8BIT400MVcmredundancySAR/ADC_redun1_tb/maestro/results/maestro/ExplorerRun.0.log'
ssh IC@192.168.225.132 'sqlite3 /home/IC/Desktop/Project/8BIT400MVcmredundancySAR/ADC_redun1_tb/maestro/results/maestro/ExplorerRun.0.rdb "SELECT * FROM resultValue;"'
```

### Modify CDAC weights (reliable)
```powershell
.venv\Scripts\python.exe -c "
from virtuoso_bridge import VirtuosoClient
c = VirtuosoClient.from_env()
# ... see Section 6 for the pattern
"
```

### Common SKILL expressions
```lisp
; Check views
ddGetObj("LIB" "CELL")~>views~>name

; Read instance
let((cv inst) cv=dbOpenCellViewByType("LIB" "CELL" "schematic" "" "r") inst=dbGetInstByName(cv "I0") ...)

; Maestro
maeGetSetup(?session "fnxSession1")
maeGetAnalysis("test" "tran" ?session "fnxSession1")
maeGetOutputValue("ENOB" "test" ?history "historyName")
```

---

## 10. Key Files

| File | Location | Content |
|------|----------|---------|
| Netlist (original, 8-bit) | `versions/v003_ADC_documentation/input.scs` | Complete Spectre netlist (818 lines) |
| README (8-bit ADC) | `versions/v003_ADC_documentation/README_TOP_redun1_ADC.md` | Full ADC documentation |
| DAC9b VA model | `sar9b_work/DAC9b_va.va` | 9-bit ideal DAC (local) |
| CDAC modify script | `sar9b_work/modify_netlist3.py` | Binary weight modification |
| Maestro run script | `sar9b_work/run_binary_final.py` | Modify weights → run → restore |
| Raw 9-bit offline script | `sar9b_work/dout9_offline_measure.py` | Export sampled `/out` + raw DOUTP-equivalent nodes, calculate FFT/SINAD/ENOB |
| DOUT logic analyzer | `sar9b_work/analyze_dout_logic.py` | Reconstruct decoder/DAC/raw-bit paths from exported waveforms |
| Phase sweep exporter | `sar9b_work/export_bip_phase_sweep.py` | Export top-level `biP<8:0>` directly from a PSF result at phase offsets |
| Iteration starter | `sar9b_work/start_scaled_binary_run.py` | Apply the 1/4-scaled binary CDAC point and trigger ADE Explorer run |
| Best iteration summary | `sar9b_work/iterations/scaled_binary_q4/README.md` | Achieved ENOB 8.717 bits raw-code |
| Current SAR9B best run | `sar9b_work/iterations/sar9b_maestro_best_q4/README.md` | SAR9B `Interactive.11`, DAC9 `/out` ENOB 7.86 bits and raw-code ENOB 7.920 bits |
| SAR9B ENOB recovery project | `projects/sar9b_enob_recovery/README.md` | Final Vpk=800m recovery result with `/out` ENOB 8.678 bits and raw-code ENOB 8.7203 bits |
| SAR9B submodule Maestro project | `projects/sar9b_submodule_maestro/README.md` | Standalone comparator, clock, async-control, and bootstrap Maestro testbenches |
| SAR9B submodule metric mapping | `projects/sar9b_submodule_maestro/docs/performance_metrics.md` | Online performance-metric references and mapping to Maestro/offline measurements |
| SAR9B submodule Maestro creator | `projects/sar9b_submodule_maestro/scripts/create_submodule_maestro_tests.py` | Creates four standalone schematic testbenches and Maestro `TRAN` views in `SAR9B_400MV` |
| SAR9B submodule run helper | `projects/sar9b_submodule_maestro/scripts/run_submodule_maestro_tests.py` | Runs Maestro, archives histories, records ADE point metrics, exports waveforms, and computes quick/offline metrics |
| SAR9B Maestro launcher | `sar9b_work/start_sar9b_maestro_best_run.py` | Starts `SAR9B_400MV/ADC_9B_tb_best_q4` Maestro runs |
| SAR9B result checker | `sar9b_work/check_sar9b_maestro_run.py` | Polls and archives SAR9B Maestro/Spectre status; success requires 0 run errors and 0 Spectre errors |
| SAR9B AHDL wrapper setup | `sar9b_work/set_sar9b_ahdl_wrapper.py` | Uploads `sar9b_va_ahdl.scs` and sets Maestro definitionFiles to the wrapper |
| CIW X11 typing helper | `sar9b_work/x11_type_text.py` | Recovery helper for reloading bridge / pressing modal dialogs through X11 |
| Latest binary raw-code results | `sar9b_work/wave_exports_binary/ExplorerRun.0/measurement.json` | Offline `/out` and raw 9-bit code metrics |
| Latest binary active netlist | `sar9b_work/wave_exports_binary/ExplorerRun.0/input.scs` | Captured binary-weight netlist from the completed Maestro run |
| Restore script | `sar9b_work/restore.py` | Restore original CDAC weights |
| Working netlist dir (remote) | `/home/IC/Desktop/Project/SAR9B_400MV/netlist_sim/` | Modified ihdl + input.scs with binary weights |

---

## 11. Known Pitfalls

1. **Never use `schCreateInst` or `schReplaceInst`** — they corrupt instances (I0 was corrupted and had to be restored)
2. **Always restore CDAC weights** after simulation — use `restore.py` if needed
3. **PowerShell quoting**: Use Python script files, not inline `-c` commands
4. **CIW blocking**: If SKILL times out, reload bridge in CIW (`RBStopAll()` then `load(...)`)
5. **"a" mode failures**: `dbOpenCellViewByType` with "a" fails for locked cells — purge `.cdslck` files via SSH first
6. **SAR9B VA cells**: Plain Maestro `definitionFiles` directly including `.va` files generates Spectre `include`, which is wrong for Verilog-A. Use `sar9b_work/set_sar9b_ahdl_wrapper.py` so Maestro includes a wrapper containing `ahdl_include` lines.
7. **Large `ocnPrint` exports can block CIW**: Always export sampled waveforms with `?from`, `?to`, and `?step`; full `/out` prints trigger >10000-point modal warnings.
8. **Top-level `biP<*>` nets are exportable**: Use `VT("/biP<0>")` ... `VT("/biP<8>")` for raw-code work. The inverse saved DFF nodes are still a validated fallback.
9. **Avoid opening/closing ADE just for exports**: `close_gui_session` can trigger an `ADE Explorer Save Setup` modal and block the bridge. For existing histories, call `openResults("<...>/psf")` directly.
10. **`maeRunSimulation` / `run_and_wait` is fragile here**: ADE Explorer may require the GUI `Update and Run` dialog. When it appears, pressing `Update and Run` starts the run; poll `ExplorerRun.0.log` and `spectre.out` through SSH.
11. **Always verify restore after failed runs**: If a script times out while a modal is open, restore can fail silently; run `sar9b_work/restore.py` and read back all cap values.
12. **SAR9B target discipline**: For the requested 9-bit flow, modify and run `SAR9B_400MV/ADC_9B_tb_best_q4`, not the older `8BIT400MVcmredundancySAR/ADC_9B_tb_best_q4` reference cell.
13. **Bridge-created schematics may need extraction metadata repair**: If new schematic testbenches fail netlisting with `OSSHNL-108` or `OSSHNL-109`, run `schCheck`, `dbSave`, `dbSetConnCurrent`, then `dbSave`; manual `connectivityLastUpdated` edits are brittle because `dbSave` advances `schGeometryLastUpdated`.
14. **Do not use text `"0"` labels as Spectre ground in generated TBs**: Wire a local `VSS_SRC` minus terminal to an `analogLib/gnd` symbol so the netlist emits `VSS_SRC (VSS 0)`. Text labels can netlist as floating `_net0`.
15. **ASYCTRL `DFFRN.RN` is active-high reset here**: In standalone ASYCTRL tests, drive `CLKS` high only for startup reset, then hold it low so `VALID` pulses can advance `CLKO<8:0>`.
16. **Do not register branch-current power expressions as IC618 Maestro point outputs**: `average(getData("/VDD_SRC/PLUS" ?result "tran"))` and `integ(...)` evaluate after `openResults`, but ADE stored outputs report `Error No`. Keep supply power/energy in `offline_metrics` and let `run_submodule_maestro_tests.py` compute them from PSF.
