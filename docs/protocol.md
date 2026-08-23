# WalkingPad local protocols

This project talks to the treadmill over Bluetooth Low Energy. The pad's own
Wi-Fi radio is not used for control.

## One-client rule

A WalkingPad accepts a single GATT client. Quit KS Fit (force-close, do not
leave it in the background) before connecting.

## Families

| Advertised name / services | Path | Notes |
| --- | --- | --- |
| `0xFE00` (A1, C1, C2, R1/R2, many KS-*) | WiLink | Proprietary `F7 … FD` frames |
| `KS-HD-*` + `0x1826` + supplement `24e2521c-…` | FTMS + unlock | Unlock token is `LE32(name[-4:]) + 1` |
| `KS-MC21-*` / `KS-SMC21C-*` / `ZP-ZEALR1-*` | FTMS + ODM | Write `01 00 0d 00 06 0b 0f 0d` to `d18d2c10-…` before each control point |

## WiLink (service `0xFE00`)

Outgoing frames on `0xFE02`:

```
F7 | TYPE | OPCODE | PAYLOAD… | Σ(TYPE..PAYLOAD) mod 256 | FD
```

Incoming status on `0xFE01` starts with `F8 A2`. Notifications can coalesce or
split; the client buffers on `F8 … FD` boundaries.

## FTMS (service `0x1826`)

Standard Fitness Machine Service. After any vendor unlock:

1. `REQUEST_CONTROL` (`00`) — some KingSmith firmwares reject this and still accept later commands
2. `START_OR_RESUME` (`07`)
3. Wait until treadmill-data speed is non-zero
4. `SET_TARGET_SPEED` (`02` + uint16 LE, km/h × 100)
5. `STOP_OR_PAUSE` (`08 01` stop, `08 02` pause)

KingSmith extends treadmill-data flag bit 13 as a step counter.

## Sources

Documented from public reverse-engineering of KS Fit and on-wire captures:

- [mill.cat PROTOCOL.md](https://github.com/knpwrs/mill.cat/blob/main/PROTOCOL.md)
- [walkingpad-controller FTMS reference](https://github.com/mcdax/walkingpad-controller/blob/main/docs/ftms-protocol-reference.md)
- [Z1 supplement unlock](https://github.com/slandau3/z1-walkingpad-mcp/blob/main/docs/protocol.md)
- [ph4-walkingpad](https://github.com/ph4r05/ph4-walkingpad)
