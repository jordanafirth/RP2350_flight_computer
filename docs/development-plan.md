# Development plan

Started: 2026-11-18. Status describes actual evidence, not intended completion.

## Sequence and completion criteria

| Step | Work | Completion evidence | Status |
| --- | --- | --- | --- |
| 1 | Capture requirements and unresolved choices | Traceable baseline, explicit assumptions, and prototype acceptance criteria | Initial baseline complete; electrical/mechanical details open |
| 2 | Acquire and audit reference designs | Pinned upstream revisions, retained licenses, CAD/net/power inventory, verified component faces | Initial audit complete; specific RP2350 Adalogger source remains unlocated |
| 3 | Select architecture and parts | MCU/sensor/power decisions, pin allocation, exact connector choices, lifecycle and quantity sourcing checks | Started: architecture and candidate pin map recorded; exact BOM and sourcing pending |
| 4 | Create integrated schematic | Editable CAD, BOM with manufacturer part numbers, power review, clean electrical-rule check with reviewed exceptions | Not started |
| 5 | Prove mechanical fit and lay out PCB | Measured placement within target outline, connector/enclosure access, routing, ground/return review, clean design-rule check, 3D inspection | Not started |
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

## Next concrete work

1. Review candidate GPIO map and power-control alternatives; battery model/capacity remains needed to set the charger current.
2. Select exact barometer, power-control connector and four-position servo header assembly with orderable manufacturer numbers. Check current supply at 2,000 and 200-unit quantities.
3. Select/install or locate a usable PCB CAD toolchain. Git is accessible; KiCad CLI was not found on PATH or the common 9.0/10.0 installation paths checked. PlatformIO launcher paths exist but were not executed or validated.
4. Create the editable integrated schematic, then a measured placement study. No CAD import, ERC, DRC, prototype test, or production quote has yet been performed.
