# Requirements baseline

Source: direct user statements in this chat, through 2026-11-19. Prior assistant suggestions are tracked separately as proposed engineering defaults.

## Confirmed

| ID | Requirement or observation |
| --- | --- |
| R01 | Initial quantity approximately 2,000, then approximately 200/year. Equipment is returned and reused each semester. |
| R02 | Replace the cable-connected RP2040 Feather Adalogger, BMP280 breakout, and BNO085 breakout with a smaller integrated assembly. |
| R03 | Prefer RP2350 for the new board. Adafruit's unreleased Adalogger development work may be a useful reference. |
| R04 | Target roughly RP2040 Feather Adalogger size, shape, and features. Exact maximum dimensions and height are not yet specified. |
| R05 | Existing Adalogger microSD socket is on its top face, per user correction. Verify downloaded CAD revision independently before using it for placement. |
| R06 | Four installed servo headers, each with power, ground, and independent signal; retain other GPIO access where practical. Existing courses use two servos. |
| R07 | Assume minimal servo power. Do not make a large dedicated servo supply a baseline requirement; battery-voltage operation is confirmed in R14. |
| R08 | Factory-installed connector for ENABLE and GND; inserted shorting plug turns computer off; removing tagged plug powers it on and starts recording. Connector type is flexible. |
| R09 | Existing logging is CSV to microSD at 50 Hz and is sufficient. |
| R10 | Flight normally about 10 s and under five minutes. Recording may include much longer pre/post-flight activity; up to four hours has occurred. This is not a four-hour battery-runtime requirement. |
| R11 | Prefer +/-16 g; existing BNO085 +/-8 g limit is accepted. |
| R12 | Small lithium-ion battery; the confirmed part and packaging arrangement are recorded in R18. |
| R13 | Five Qwiic connectors and 3 V/5 V interface level shifting need not be retained. |
| R14 | Current nominal-5 V micro servos work directly from the single-cell battery in hand-tossed 250 mm balsa gliders. Preserve battery-voltage servo power as the baseline; no 5 V boost supply required. |
| R15 | Application firmware is Arduino in PlatformIO (user calls the setup pioarduino). User will write it separately; sensor outputs and CSV schema are outside this hardware-development scope. |
| R16 | BNO085 is the intended minor upgrade to the BNO080 reference circuit. A shared BNO080 CAD symbol is expected and is not a reason to change the sensor. |
| R17 | No display connector on the custom board. |
| R18 | Battery is Adafruit PID 3898, 3.7 V 400 mAh. Mount it beneath the PCB with clearance for underside sensors; keep its socket on top in the standard Feather location. |
| R19 | Prefer horizontal, side-entry Qwiic connectors; user reports the vertical connectors seem weak. |
| R20 | If USB and SD do not fit on a long edge, putting both at the same short end would be desirable. Put the four servo ports at the opposite end. |
| R21 | Use right-angle servo pins so the mating cables exit through the far end. |

## Proposed engineering defaults (not user commitments)

- Retain BNO085 initially; do not add a second accelerometer by default.
- Choose a current-production replacement barometer rather than commit a new production design to BMP280.
- Prefer RP2350 A4 silicon; confirm exact orderable part and supply.
- Preserve Feather mounting and header positions where compatible with the four servo headers and integrated sensors.
- Retain one Qwiic/STEMMA QT expansion port if placement permits.
- Retain USB-C, onboard charging, boot/reset access, status indication, and microSD.
- Keep sensors and microSD on the switched logic supply. Servo supply must obey the chosen off behavior as well.
- Target four PCB layers for the first placement/routing assessment; select assembly faces based on fit and cost.
- Provide hardware pin documentation suitable for the user's Arduino/PlatformIO application. Limit firmware work here to a minimal manufacturing/bring-up test if needed.

## Open inputs, ordered by when needed

| Input | Why it matters | Needed before |
| --- | --- | --- |
| Servo exact model (useful, not blocking reference audit) | Baseline raw-battery power is now confirmed by the working system; check mating clearance, logic threshold, and supply-switch rating | Connector/power detail review |
| Battery details | Resolved: Adafruit PID 3898, 400 mAh, protected, Adafruit-polarity JST-PH | Verify actual socket and clearance during design review |
| Confirmation that the proposed pin map is convenient | Hardware assignments will be documented; no port of the application, sensor reports, or CSV fields is requested | Pin allocation freeze |
| Required unused GPIO/interfaces | Resolve conflicts with sensors, SD and four servo outputs | Pin allocation freeze |
| Required maximum dimensions/height and mounting/enclosure | Assess whether Feather outline and underside placement actually fit | Layout freeze |
| Tag behavior with USB connected, and shutdown workflow | Define charging/service mode and SD file handling | Power-control freeze |
| Whether +/-16 g is worth an additional part or sensor change | Determines whether accepted +/-8 g baseline should change | Sensor schematic freeze |
| Budget and semester deadline | Choose sourcing, prototype schedule and production route | Quote selection |

## Scope boundaries

This project is a teaching flight data logger with servo outputs. No deployment/ignition hardware or autonomous flight-control behavior has been requested. Proposed improvements must be explicitly identified rather than silently expanding the baseline.
