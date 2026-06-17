# Root-Cause Note: SAR9B ENOB 7.86

Date: 2026-06-17

## Observation

The final SAR9B Maestro run reports:

```text
spectrum_enob_p2200  7.86
spectrum_sinad_p2200 49.08
spectrum_enob        7.86
spectrum_sinad       49.08
```

The repaired raw-code path from the same SAR9B state gives:

```text
SINAD = 49.4385 dB
ENOB  = 7.9200 bits
code range = 125..386
```

This is lower than the earlier q4-scaled binary experiment:

```text
SINAD = 54.2347 dB
ENOB  = 8.7167 bits
code range = 24..487
```

## Evidence

The q4-scaled CDAC weights match between both runs:

```text
64, 32, 16, 8, 4, 2, 1, 0.5, 0.25 Cu
```

The dominant difference is input amplitude:

| Run | Netlist Vpk |
|-----|-------------|
| `scaled_binary_q4/input.scs` | `800m` |
| `sar9b_maestro_best_q4/input.scs` | `450m` |

Signal-power ratio:

```text
8.8976e9 / 2.8062e10 = 0.3171
(450 / 800)^2        = 0.3164
```

SINAD loss from amplitude alone:

```text
20 * log10(800 / 450) = 4.998 dB
4.998 dB / 6.02       = 0.83 bits
```

Observed raw-code loss:

```text
54.2347 dB - 49.4385 dB = 4.7962 dB
8.7167 bits - 7.9200 bits = 0.7967 bits
```

## Conclusion

The present 7.86-bit DAC9 `/out` result is mostly an input-amplitude/setup
issue, not proof that the 9-bit SAR core is intrinsically limited to 7.86 bits.

The setup is internally inconsistent:

- `active.state` contains `Vpk=800m`.
- `maestro.sdb` contains repeated active run blocks with `Vpk=450m`.
- The generated `Interactive.11` netlist uses `Vpk=450m`.

Therefore the next step is to remove or patch the hidden `Vpk=450m` Maestro
override, rerun at `Vpk=800m`, and then remeasure both raw `biP<8:0>` and DAC9
`/out`.

## Verification Run

The follow-up run confirmed the hypothesis. Because an already-open ADE session
can write stale `450m` values back into `maestro.sdb`, the successful flow used
`maeSetVar` on the live Maestro session before saving and running.

| Item | Value |
|------|-------|
| Run | `SAR9B_400MV/ADC_9B_tb_best_q4` `Interactive.12` |
| Live-session readback | `maeGetVar("Vpk") -> "800m"` |
| Netlist parameter line | `parameters fs=400M Vpk=800m Cunit=1f Vth_sw=0.9 TSTOP=2.7u` |
| Spectre result | 0 errors, 40 warnings, 8 notices |
| Spectre elapsed | 36m 58.5s |
| Maestro default `/out` outputs | SINAD 54.01 dB, ENOB 8.678 bits |
| Raw `biP<8:0>` best | SINAD 54.2559 dB, ENOB 8.7203 bits |
| Raw best phase | `+1500 ps` |
| Raw code range | 24 to 487 |
| DAC9 `/out` phase-sweep best | SINAD 54.1370 dB, ENOB 8.7005 bits |
| DAC9 `/out` best phase | `+2250 ps` |

This closes the root cause: the previous ENOB `7.86` was caused primarily by
the hidden `Vpk=450m` Maestro override. With the intended `Vpk=800m`, both the
raw SAR output and the repaired 9-bit DAC measurement chain recover to about
`8.7` ENOB.
