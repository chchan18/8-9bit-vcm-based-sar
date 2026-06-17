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
