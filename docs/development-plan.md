# Development plan

Started: 2026-11-18. Status describes actual evidence, not intended completion.

## Sequence and completion criteria

| Step | Work | Completion evidence | Status |
| --- | --- | --- | --- |
| 1 | Capture requirements and unresolved choices | Traceable baseline, explicit assumptions, and prototype acceptance criteria | Initial baseline complete; electrical/mechanical details open |
| 2 | Acquire and audit reference designs | Pinned upstream revisions, retained licenses, CAD/net/power inventory, verified component faces | Initial audit complete; specific RP2350 Adalogger source remains unlocated |
| 3 | Select architecture and parts | MCU/sensor/power decisions, pin allocation, exact connector choices, lifecycle and quantity sourcing checks | Major selections made; remaining exact BOM entries and production sourcing pending |
| 4 | Create integrated schematic | Editable CAD, BOM with manufacturer part numbers, power review, clean electrical-rule check with reviewed exceptions | Initial integrated KiCad draft generated; ERC and conversion/connectivity checks run; independent engineering review and BOM completion remain |
| 5 | Prove mechanical fit and lay out PCB | Measured placement within target outline, connector/enclosure access, routing, ground/return review, clean design-rule check, 3D inspection | Initial native placement generated; clearance, mechanical review and routing remain open |
| 6 | Prepare and order engineering prototypes | Assembler-reviewed fabrication/assembly package, sourcing quote, programming/test plan; suggested first batch 5-10 boards | Not started; ordering is a later explicit action |
| 7 | Bring up and validate | Power measurements, functional tests, recording continuity, servo interaction, power-cycle/recovery and flight comparison | Requires physical boards |
| 8 | Classroom pilot and production release | Suggested 20-50 unit pilot, corrected revision if needed, fixture and work instructions, released package and accepted production quote | Requires pilot evidence |

Batch sizes are planning proposals, not purchase commitments. Do not order 2,000 units directly from an untested first revision.

## Current work

1. Record user-confirmed requirements and avoid treating prior assistant suggestions as requirements.
2. Completed: retrieved RP2040 Adalogger, RP2350 Feather, BNO08x, and BMP280 CAD as reference inputs, retaining exact revisions and license files.
3. Look for the specific RP2350 Adalogger CAD. If it cannot be located, proceed with the published RP2350 Feather processor/power circuit and RP2040 Adalogger storage circuit as separate references. Do not label either as the unreleased Adalogger.
4. Completed initial extraction of reference net connections, component sides, outline, regulator/charger parts, and used GPIO. Candidate custom allocation is documented separately.
5. Draft a measured component placement before committing to an underside-only sensor arrangement.

## Prototype acceptance criteria (proposed)

- Tag inserted: intended logic and servo supplies off; quantify remaining battery drain. Tag removed: reliable boot and automatic recording.
- USB charging and battery operation work with the selected battery and charge current. No unintended powering through servo signals or USB paths.
- All four servo outputs operate while sensor logging continues at the requested 50 records/s. Define a timestamp-gap limit with the existing firmware before testing.
- With minimal test firmware, record for at least five minutes and perform a four-hour bench soak using an adequately sized supply; inspect timestamp continuity, sensor resets, lost records, and file readability. Four-hour battery endurance is not assumed. The user supplies the course application separately.
- Validate shutdown/file handling, repeated starts, full/missing/failed SD card, and low battery behavior. Define the accepted amount of recent data loss on abrupt removal of power.
- Confirm barometer and BNO085 communication and basic plausible measurements; application sensor-output selection is outside scope.
- Check pressure-port clearance/venting, sensor-axis labeling, connector retention, mounting, and battery restraint in the intended package.
- Program and functionally test through a repeatable fixture procedure suitable for manufacturing and semester returns.

## Release gates

Schematic release requires the battery, servo voltage, power-control behavior, connectors, and GPIO map to be resolved. Layout may explore placeholders beforehand, but it is not a manufacturing release.

Production release requires physical prototype and pilot results. CAD checks and simulated behavior cannot substitute for those results.

## Work log

- 2026-11-18: Created repository documentation. Recorded confirmed requirements and separated design proposals. Began upstream CAD acquisition and local-tool inventory.
- 2026-11-18: Acquired 20 reference files across four pinned upstream repositories, including 10 Eagle CAD files and four license files. Verified SHA-256 hashes and parsed CAD into a repeatable inventory. Confirmed top-face Adalogger SD socket and measured 50.8 x 22.86 mm outline endpoint spans. Recorded initial findings and candidate GPIO allocation.
- 2026-11-18: User confirmed low-current nominal-5 V servos powered directly from the battery, hand-tossed 250 mm balsa gliders, and Arduino/PlatformIO application firmware written separately. Sensor-output and CSV-format work excluded. Shared BNO080 symbol accepted as the reference for BNO085.
- 2026-11-18: Added and audited pinned BMP5xx reference source. Found installed KiCad 10.0.3 in the current-user installation and successfully exercised its schematic/board import and CLI checks.
- 2026-11-18: User excluded the display connector and identified battery PID 3898 (400 mAh), beneath the PCB with sensor clearance and its socket in the standard Feather location on top. Retained the reference 5.1 kilohm charge setting, about 196 mA nominal.
- 2026-11-18: Generated an integrated four-sheet hardware draft plus root, containing 94 footprint-bearing items (including test pads and unpopulated expansion headers); seven nonphysical ERC power flags are additional schematic symbols. Added reproducible generation, source-footprint geometry checks and independent KiCad netlist comparison. No PCB placement/routing or manufacturing release exists yet.
- 2026-11-18: Complete rebuild passed with zero ERC violations, 346 connected pads and 25 named hardware requirements checked against the KiCad export, plus conversion-fidelity checks of 26 source-derived footprints / 213 source pads. Markdown files retain LF endings.

## Next concrete work

Latest placement checkpoint: native PCB generated with all 94 schematic items, four mounting holes and a battery envelope. The Qwiic socket remains horizontal. USB4110 uses SMT shell stakes, and the two-pin tag connector is top-entry. Schematic checks pass with zero ERC violations, 351 connected pads and 25 named requirements checked; source conversion checks cover 25 footprints and 197 pads. PCB schematic parity is clean, but the PCB is unrouted and its DRC report has outstanding violations. No assembly quote has been obtained.

1. Independently review the integrated circuit connections and selected manufacturer packages; complete the exact BOM. Major choices and procurement observations are in `parts-selection.md`.
2. Verify footprint suitability beyond conversion fidelity, including paste/mask and exposed pads. Current check evidence is in `reports/schematic/`.
3. Refine the initial native PCB placement with battery underneath, battery socket on top, USB and SD being assessed at one short end, four servo ports at the other end, a horizontal Qwiic connector, and no display connector. The starting battery clearance and component fit are not yet validated. The current board is unrouted and has outstanding DRC issues.
4. Route the board only after the placement and schematic reviews. DRC, prototype tests, a complete production quote and manufacturing approval are still outstanding.

The 2026-11-18 placement generator is `tools/place-pcb.py`; its output is `hardware/rev-a/flight-computer.kicad_pcb`. Its report and KiCad DRC output are under `reports/pcb/`. The all-SMT USB4110 candidate avoids through-hole USB shell stakes beneath the SD socket. Locating pegs, socket keepouts, card ejection, battery clearance and the exact SD socket still need review. Keep the Qwiic socket horizontal per the user's explicit preference.
