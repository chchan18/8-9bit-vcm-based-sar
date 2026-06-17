# Session Log: SAR9B ENOB Recovery Project

Date: 2026-06-17

## Request

Explain why the 9-bit SAR ADC currently reports only ENOB `7.86`, and open a
new project to try solving the issue.

## Findings

The repaired SAR9B DAC9 measurement chain is valid, but the final run was
under-driven:

- `SAR9B_400MV/Interactive.11` netlist used `Vpk=450m`.
- The earlier q4-scaled binary run that reached raw-code ENOB `8.7167` used
  `Vpk=800m`.
- Code range dropped from `24..487` to `125..386`.
- Signal power dropped by almost exactly `(450/800)^2`, while noise/distortion
  power stayed nearly unchanged.

This explains about `0.8 bit` of ENOB loss, matching the observed difference
between raw-code ENOB `8.7167` and `7.9200`.

## Project Created

New project directory:

```text
projects/sar9b_enob_recovery/
```

Key files:

- `README.md`
- `analysis/2026-06-17_root_cause.md`
- `experiment_matrix.csv`
- `scripts/patch_maestro_vpk.py`
- `scripts/upload_vpk800_setup.py`
- `artifacts/maestro_files_vpk800_p2200/`

## First Artifact

The local Maestro setup patcher generated:

```text
projects/sar9b_enob_recovery/artifacts/maestro_files_vpk800_p2200/
```

Patch manifest:

```text
active.state: 1 x 800m -> 1 x 800m
maestro.sdb:  12 x 450m + 12 x 800m -> 24 x 800m
```

## Follow-up Run Completed

The first experiment was completed in `SAR9B_400MV/ADC_9B_tb_best_q4` as
`Interactive.12`. A pure XML upload was not enough because an already-open ADE
session could save stale in-memory `Vpk=450m` values back into `maestro.sdb`;
the successful flow used live-session `maeSetVar` calls before saving and
running.

Netlist evidence:

```spectre
parameters fs=400M Vpk=800m Cunit=1f Vth_sw=0.9 TSTOP=2.7u
```

Results:

Maestro default p2200 outputs:

```text
spectrum_enob_p2200  8.678
spectrum_sinad_p2200 54.01
spectrum_enob        8.678
spectrum_sinad       54.01
```

| Path | Best phase | SINAD | ENOB | Notes |
|------|------------|-------|------|-------|
| Raw `biP<8:0>` | `+1500 ps` | 54.2559 dB | 8.7203 bits | Code range 24 to 487 |
| DAC9 `/out` phase sweep | `+2250 ps` | 54.1370 dB | 8.7005 bits | 42.27 mV to 857.73 mV |

Spectre completed with 0 errors, 40 warnings, and 8 notices in 36m 58.5s.

Conclusion: the previous SAR9B ENOB `7.86` result was primarily caused by the
hidden `Vpk=450m` Maestro override. The repaired 9-bit DAC measurement chain is
reasonable after the intended `Vpk=800m` setup is forced into the live Maestro
session.
