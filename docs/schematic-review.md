# Integrated schematic draft: review notes

The project is `hardware/rev-a/flight-computer.kicad_pro`. Open its same-named `.kicad_sch` for the root and four functional sheets. This is a connectivity-first development draft with project-local symbols, not a released PCB design.

## Implemented

- RP2350 Feather processor/USB/charger/regulator circuit with a documented custom GPIO map.
- No display/HSTX connector. No optional PSRAM component or its dedicated pull-up. The untouched vendor references still contain their original features.
- BNO085 directly on 3.3 V I2C, with reset and interrupt connections, boot/mode straps, auxiliary-bus pull-ups, CAP bypass and the reference 32.768 kHz crystal circuit.
- BMP581 directly on that bus, with SDO grounded for address 0x46 and interrupt routed to GPIO19.
- SPI1 microSD; SPI0 remains available at the expansion pads.
- Four servo signals with independent PWM resources. Header columns are signal, battery supply and GND, with battery in each plug's center position.
- Direct-battery servo voltage through a small ENABLE-controlled load switch. This is not a regulated 5 V servo supply.
- Factory-populated tag connector between ENABLE and GND; tag inserted disables logic and servo rails.
- 400 mAh Adafruit PID 3898 battery with approximately 196 mA nominal charging using the reference 5.1 kilohm programming resistor.

## Defined power behavior

| Condition | Intended behavior |
| --- | --- |
| Battery connected, tag removed | Logic runs and battery-voltage servo supply is enabled |
| Battery connected, tag inserted | Logic regulator and servo switch are disabled; battery/charger circuitry remains connected |
| USB connected, tag inserted | Battery can charge while logic and servos are disabled |
| USB connected, tag removed | Logic runs; servos draw from battery, while charging may also occur |
| USB only, battery absent | Logic may run; servo battery supply is unavailable |

The tag remains a hard power-off input. There is no hold-up or firmware shutdown handshake. Reinsert only after the application has handled its file-writing policy. Application firmware is supplied by the user.

The simple retained charger is not a separate battery power-path controller. Servo load while charging can affect charge termination; inserting the tag for charging removes that load. Bench validation must include this behavior.

## Layout envelope

- Begin at approximately 50.8 x 22.86 mm, with Feather mounting/header geometry where possible.
- Put battery beneath the PCB, with a mechanical gap for underside sensors and solder joints. Keep its socket on top in the standard Feather location.
- A nominal 3 mm underside gap is the current placement-study proposal. Verify sensor height, header tails, solder fillets, insulation, battery tolerances and retention before approving it.
- Battery starting envelope is approximately 36 x 17 x 7.8 mm. Do not place adhesive or foam over the barometer pressure opening. Provide a path for ambient pressure to reach the sensor.
- The selected right-angle servo header has an approximately 8.13-mm triple-row body envelope above the PCB and projects 5.58 mm beyond the end. Mating plugs and cables need additional clearance. Actual enclosure height is not yet established; see `placement-review.md` for the manufacturer-drawing review.

## Validation and limitations

- KiCad 10.0.3 parses and exports the draft. Current detailed check results are in `reports/schematic/`.
- Current check evidence is retained in `reports/schematic/erc.json`, `connectivity-check.json` and `footprint-check.json`. The latest draft contains 92 footprint-bearing items: 86 fitted components, three copper test pads and three DNP items (J1/J2 and D5). USB data test pads were removed during routing to avoid test stubs. Source-conversion checks do not qualify newly selected standard-library packages or prove physical assembly suitability. The custom right-angle servo footprint was reviewed against the Samtec print and hole pattern; prototype inspection remains required.
- `check-connectivity.py` compares the independently exported KiCad netlist against the intended per-pad model and checks named sensor, tag, switch and servo connections.
- ERC is necessary but cannot establish correct footprints, physical fit, supply transient behavior or sensor performance. A clean check would not constitute manufacturing approval.
- Pin types for BNO085 SA0 and BMP581 SDO are inputs in this selected I2C configuration, even though shared SPI-oriented source symbols label them differently.
- Connector mounting contacts are modeled as passive metal contacts. The source geometry check caught and corrected a 1 mm test-pad diameter that had initially been recreated as 1.27 mm.
- Expansion headers J1/J2 retain their pads and connections but are DNP. D5 is also DNP because its rated minimum supply exceeds 3.3 V. The three boot/SWD test pads are excluded from the assembly BOM: TP3 is USBBOOT, TP4 is SWDIO and TP5 is SWCLK. A programming fixture also needs an existing ground pad. Servo, tag, battery and Qwiic connectors remain fitted in the draft.
- Power flags describe external supplies and supply paths through passive components. They do not add hardware or simulate voltage regulation.
- Converted reference boards are used for footprint extraction only. KiCad reported skipped inner-layer polygons on Feather imports. Their imported routing must not be used as a validated replacement for the original boards.

## Remaining before schematic release

1. Independently compare every IC pin and power connection against manufacturer documentation, including the selected RP2350 stepping/package.
2. Verify all project-local pad numbers, pad sizes, rotations, paste/mask apertures and thermal-pad treatment; verify the custom servo-header drawing against the manufacturer dimensions.
3. Qualify and source the assigned flash, microSD, crystal, USB, MOSFET, diode, LED and passive manufacturer part numbers. Every fitted item has a candidate MPN; this does not establish availability or approval for substitution.
4. Perform the measured component placement study, then review routing and test access.
5. Validate battery/USB switching, tag operation, charging, sensor reset/startup and simultaneous servo/logging operation on prototypes.
