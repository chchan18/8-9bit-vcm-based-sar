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

Next step: upload the patched setup, run a fresh SAR9B Maestro simulation, and
verify the new captured netlist uses `Vpk=800m`.
