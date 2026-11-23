# Placement and mechanical review

Updated 2026-11-23. This is an engineering development record, not a manufacturing release.

2026-11-20 routing update: USB series resistors R9/R10 are on the processor face, with explicit processor-side traces about 5.16 and 4.16 mm long. The interleaved USB-C contacts have fixed local jumps, and the long parallel route is on the bottom with reserved L3 ground beneath it. The inherited USB data test pads were removed. Processor regulator/decoupling connections and the short IMU crystal circuit are also explicitly routed. See `routing-review.md` for geometry and validation limits. Both inner layers carry signals and ground fill; L2 is not a continuous ground plane. USB reference reservations are retained. The candidate stackup is now recorded in native CAD, with fabricator impedance confirmation still pending.

The completed four-layer routing connects every signal and ground net. Current native checks are recorded in `reports/pcb/current-drc.json`, with a board hash in `reports/pcb/routing-completion.json`. Only the three intended processor ground vias overlap solder lands and require the specified filled/capped process. The two reviewed locating-hole notices below remain separate from electrical clearance/connectivity checks.

## Current arrangement

- PCB outline: 50.8 x 22.86 mm, with the reference Feather GPIO-hole positions retained.
- USB-C on top and microSD underneath at the same short end. The SD socket is Molex 1040310811, a compact push-pull part with card detection; its body is 11.95 x 11.40 x 1.42 mm. Card extraction and simultaneous access with the actual classroom USB cable need a physical check.
- Four servo ports at the opposite short end, using a factory-installed right-angle Samtec TSW-104-08-T-T-RA. The user explicitly selected cables exiting through the end. The 3 x 4 hole matrix stays on a 2.54-mm grid; the manufacturer recommends 1.02-mm finished holes.
- The right-angle header's nominal body front is at board X=50.54 mm, with posts reaching X=56.38 mm. Reserve space beyond the PCB for the mating servo plugs and cable bend. Hole numbers are project electrical numbering; the three contacts of each channel are signal, battery, and ground.
- One horizontal, side-entry Qwiic connector, JST SM04B-SRSS-TB(LF)(SN) candidate. No display connector.
- Battery socket on top in its reference Feather position; PID3898 battery underneath. Use a 36 x 17 x 7.8 mm starting battery envelope. A proposed 3-mm minimum PCB-to-battery gap clears the 1.42-mm SD socket, sensor packages and nominal 0.69-mm exposed right-angle header tails. Confirm actual assembled heights, solder and battery tolerances before fixing the carrier.
- M2 nonconductive mounting hardware, maximum head/standoff diameter 3.8 mm, with 2.2-mm clearance holes. Centers are X=2.54/48.26 mm and Y=2.14/20.72 mm in the reference lower-left coordinate system. Each Y row moved outward by 0.4 mm for connector clearance. This mounting grid differs from a stock Feather.

## Reviewed locating-hole notices

KiCad flags the two USB locating holes inside the underside SD socket's courtyard. These are intentional blind peg engagements within a through-drilled PCB hole; they are not through-board solder tails. GCT's section drawing shows approximately 0.7-mm peg projection. Even allowing the drawing's 0.3-mm general tolerance and a 1.6-mm PCB at -10% thickness gives 0.44 mm before reaching the underside surface. Retain the notices in the raw DRC report and identify this explanation to the assembler; confirm the supplied USB4110 revision before approving production.

This exception applies only to the two USB locating holes under JSD1. It does not waive any routing, copper, mounting-hardware or other component collision.

## Still required

1. Preserve the completed routing and rerun native connectivity/clearance checks after any change.
2. Review the USB pair, RP2350 regulator/clock loops and sensor decoupling after routing; an autorouter result alone is insufficient.
3. Choose the fabrication stackup explicitly. JLC04161H-3313 is the current candidate: nominal 0.0994-mm outer prepregs, 1-oz outer and 0.5-oz inner copper. USB requires a 90-ohm differential geometry checked against the fabricator's selected stackup.
4. Inspect the complete assembly with actual battery, servo plugs, USB plug and SD card. Check tag extraction, Qwiic cable clearance, mounting hardware, barometer venting and battery restraint.
5. Assemble and test engineering prototypes before a classroom pilot or production order.
6. Finish connector/function silkscreen, including servo signal/battery/GND order, channel numbers and tag/boot/reset identification.

## Manufacturer references

- [Samtec selected right-angle header](https://www.samtec.com/products/tsw-104-08-t-t-ra), [series print](https://suddendocs.samtec.com/prints/tsw-xxx-xx-xxx-x-xx-xxx-mkt.pdf), and [recommended hole pattern](https://suddendocs.samtec.com/prints/tsw-xxx-xx-x-x-xx-xxx-footprint.pdf). Relevant print: Fig. 5, Table 1 and Table 5, lead style -08.
- [Molex 1040310811](https://www.molex.com/en-us/products/part-detail/1040310811) and [manufacturer socket comparison](https://www.content.molex.com/dxdam/b7/b7c4a180-3a4a-44bc-bd65-408f8e5b6187/987652-0671.pdf).
- [GCT USB4110](https://gct.co/connector/usb4110) and [manufacturer section drawing mirrored by distributor](https://datasheet.octopart.com/USB4110-GF-A-Global-Connector-Technology-datasheet-137417970.pdf).
- [Battery PID3898](https://www.adafruit.com/product/3898).
- [Fabricator stackups](https://jlcpcb.com/impedance).
