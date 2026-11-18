# Initial reference-design findings

Audit date: 2026-11-18. Reproduce the local inventory with `tools/audit-eagle.ps1`. Exact upstream commits, URLs and SHA-256 hashes are in `references/manifest.json`; full net/part inventories are in `reports/reference-audit.json`.

## Evidence and implications

| Finding from pinned source | Implication for this project |
| --- | --- |
| RP2040 Adalogger `X2` is `MicroSD`, package `MICROSD`, rotation `R...` without mirror | SD is on top, as the user stated. Earlier assistant descriptions of an underside SD socket were incorrect. |
| Both Feather board outlines have layer-20 wire endpoint spans of 50.8 x 22.86 mm | Good starting outline; rounded extrema, edge clearances and exact hole geometry still require CAD review. |
| Adalogger has only three bottom elements with copper contacts: USB D+/D- and boot test pads; other bottom elements are graphics/labels | No mounted underside components were found in this pinned revision. Your underside-sensor proposal has a good starting basis, subject to routing and clearance checks. |
| Both Feather references use `RT9080-3.3` and `MCP73831T-2ACI/OT` | Candidate shared regulator/charger circuit; review actual datasheets and battery charge setting before reuse. |
| RP2350 Feather processor device is `RP2350_QFN60` but value is `DNP` | Normalize the production BOM and assign an actual RP2350 order code. A literal value-based BOM export is insufficient; this does not prove the reference board omits its processor. |
| BNO08x reference uses a `BNO080` device/value in the BNO085 repository | Expected shared circuit for the user's BNO085 choice. Assign BNO085 explicitly in the custom BOM; this is not a compatibility blocker. |
| BNO breakout includes AP2112 regulator, level-shifting circuitry, and 74AHC4050 buffer | Shared 3.3 V design can omit breakout-only interfaces, while retaining necessary pulls, mode straps, clock and capacitors. Removing these circuits requires intentional rewiring. |
| Adalogger SD uses GPIO18/19/20/21/22/23 with card detect on GPIO16 | Copying its pin map would conflict with standard RP2350 Feather expansion pins and its GPIO21 status LED. A custom map is required. |
| RP2350 Feather routes its display connector onto GPIO12-19 and includes optional PSRAM on GPIO8 | Omitting those unrequested features makes room for a separate SD SPI bus and sensor controls. |
| All four downloaded license files identify CC BY-SA 3.0 Unported | Keep license and source notices with references and plan attribution/change notices for derivatives. |

## What the initial audit does not establish

- The unreleased RP2350 Adalogger's editable hardware CAD has not been located. The downloaded RP2350 reference is the standard HSTX Feather.
- No custom schematic or board has been created or electrically checked.
- No manufacturing BOM, component availability, quote, assembly yield, sensor accuracy, battery endurance or physical fit has been validated.
- Automated endpoint bounds and face classification are source-data inspection, not complete CAD rendering, assembly collision checking, ERC or DRC.
- Manufacturer datasheets must be checked for every exact part and footprint during circuit design.

## Initial architecture decision

Proceed with the RP2350 Feather and RP2040 Adalogger as separate circuit references rather than wait indefinitely for the unreleased combined board. Keep BNO085. Preserve the user's direct-battery servo supply and omit a boost converter. Keep +/-16 g as an optional later decision. Prepare the integrated schematic after exact power/connector parts are selected.

## Checks performed

- All 20 downloaded reference files checked against their recorded SHA-256 hashes; all 10 downloaded Eagle CAD files parsed successfully.
- Candidate SD SPI1, expansion SPI0 and four independent servo PWM functions cross-checked against the pinned RP2350 reference symbol (10 alternate-function checks).
- This verifies the candidate map against the source symbol, not independently against the manufacturer datasheet; datasheet/package review remains a schematic task.
