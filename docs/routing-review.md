# Routing development review

Updated 2026-11-20. The working-board state and remaining connections are recorded in `development-plan.md` and the raw current DRC report. These notes describe engineering candidates, not a fabrication release.

## Fixed local circuits

The BNO085 support placement now puts Y2 beside its crystal pins. Explicit bottom-layer connections from the sensor to each crystal terminal are about 2.29 mm, with about 1.88 mm from each crystal terminal to its 22-pF load capacitor. The sensor's local supply and internal-capacitor connections are also fixed before global routing. Crystal startup still requires prototype verification.

The processor buck converter has an explicit LX path, input capacitor connection, local PGND return through the input/output capacitor grounds, and a separate feedback path from the output. The three processor core-supply decouplers remain 100 nF. C7 moves beside the top DVDD pin; the supply distribution and local capacitor connections are routed explicitly. This follows the priorities in the [RP2350 hardware design guide](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-008280-DS-2-hardware-design-with-rp2350.pdf). Bench rail measurements and transient testing remain required.

USB-C has interleaved duplicate data contacts. Short fixed jumps connect them without a crossing. The long parallel portion runs on the bottom copper, referencing ground on L3; rule areas reserve that reference from signal tracks. The processor-side data traces and series resistors are on top, referencing L2 ground. Transition ground vias connect the reference layers.

USB dimensions of 0.13-mm width and 0.13-mm gap are provisional for the candidate JLC04161H-3313 stackup. They have **not** been verified as 90 ohms. The two long parallel traces are approximately 34.75 and 35.61 mm; the local connector and resistor fanouts add length. Fabricator impedance confirmation and USB enumeration/transfer testing remain open. The [fabricator stackup table](https://jlcpcb.com/impedance) is the dimensional source.

Explicit processor escapes avoid trapping the QSPI flash signals behind the USB traces. Further staggered through-via escapes serve selected top-row GPIO and I2C pins. Ordinary vias use 0.4-mm copper / 0.2-mm finished drill and are tented on both faces. The three ground vias in the processor exposed pad require selective filling and copper capping, with an assembler-reviewed stencil/process. The [fabricator's via-treatment guidance](https://jlcpcb.com/help/article/pcb-via-covering) requires identifying the selected vias in the quotation package.

## Independent checks and their limits

- Native KiCad DRC checks copper, holes, placement and connectivity after zone refill. Scratch boards receive the actual project rules and footprint-library context.
- The importer verifies that every fixed track/via retains its UUID, geometry, width, layer and net. Freerouting's SES writer omits system-fixed copper, so replacing all original tracks would discard those critical connections.
- Outer ground pours are omitted from the routing interchange and restored/refilled on the native PCB. The routing input retains L2 ground, and L3 carries signal routing outside the USB reference reservations.
- A via-drill versus solder-land screen rejects unintended via-in-pad sites. Only the three specified processor exposed-pad vias are accepted automatically.
- A saved-fill screen samples the L3 ground directly beneath bottom-layer USB trace centers and flags nearby foreign vias. It excludes samples within 0.8 mm of USB transition vias; those transition regions require separate return-path review. This is a geometric check, not a field solver.
- Placement preservation now includes rotation and component face, as well as coordinates, so regenerating an unrouted placement can retain the checked arrangement. Regenerating placement still overwrites routed copper.

Two reviewed USB locating-hole notices remain documented in `placement-review.md`. They do not excuse electrical or other mechanical violations. No manufacturing-ready package or vendor assembly quote exists yet.
