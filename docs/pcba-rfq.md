# PCBA quotation preparation

Status 2026-11-20: incomplete engineering design. No vendor quote has been received. This document is a draft scope for a later inquiry, not authorization to fabricate or purchase.

## Quantities to price separately

| Build | Requested pricing basis |
| --- | --- |
| Engineering prototypes | 5 and 10 assembled boards |
| Classroom pilot | 50 assembled boards, after prototype corrections |
| Initial production | 2,000 assembled boards, after pilot acceptance |
| Replacement production | 200 assembled boards per year; state minimum order and setup charges |

## Assembly scope

- Approximately 50.8 x 22.86 mm, four-layer, nominal 1.6-mm PCB. JLC04161H-3313 is recorded as the candidate stackup in native CAD and `reports/pcb/fabrication-settings.json`; fabricator confirmation and USB impedance verification remain open. Quote lead-free assembly and ENIG as the starting finish. Do not substitute a stackup without reviewing USB geometry.
- Populate both faces from the released BOM and centroid files. Current draft has 86 fitted items, including one through-hole servo header. Use exact part numbers for ICs, oscillators and connectors; return any proposed substitutes for review.
- Processor SC1509-A4, BNO085 IMU, BMP581 barometer, QSPI flash, charging and switched logic/servo supplies.
- Factory-install all connectors, including Samtec TSW-104-08-T-T-RA right-angle servo header. Solder all 12 contacts; mating cables leave the end. Maximum nominal post projection extends 5.58 mm beyond the PCB.
- Install horizontal JST SH Qwiic, top-side JST PH battery socket, JST SH two-pin tag socket, USB-C and underside microSD socket. USB and SD share the opposite end from the servo ports.
- J1/J2 expansion headers and D5 optional RGB LED are DNP. Copper test pads are PCB features, not purchased assembly items.
- Supply a factory-made mating shorting harness: JST SHR-02V-S-B, two SSH-003T-P0.2-H contacts, a short 28-AWG loop, and a REMOVE BEFORE FLIGHT tag. Verify that its two contacts are shorted, with no connection to battery power.
- Quote the shorting harness/tag, a microSD card, and battery separately from the PCBA. Battery reference is protected Adafruit PID3898, 3.7 V 400 mAh, Adafruit-polarity JST PH; the PCB's charge current is approximately 196 mA.
- Review USB locating-peg engagement over the underside SD socket as documented in `placement-review.md`. Four M2 mounting centers differ from stock Feather Y spacing by 0.4 mm per row.
- The current candidate has three 0.4-mm-diameter / 0.2-mm-drill GND vias in the RP2350 exposed pad. Quote these as epoxy filled and copper capped; exact coordinates are recorded in `reports/pcb/fabrication-settings.json`. Ordinary vias are tented on both faces. The selected sites avoid the underside BNO lands and lie between the inherited paste windows. Include a selective via-treatment drawing and require assembler review of stencil coverage, via treatment and the two-sided process before release.

## Requested quote details

Separate PCB fabrication, component procurement, SMT/through-hole assembly, harness/tag manufacture, programming/test, tooling/setup, sourcing surcharges, freight and lead time. State currency, validity, yield/overage policy, component ownership and replacement-batch setup charges. Identify shortages and lifecycle risks, especially BNO085 and the A4 processor.

Application firmware is supplied separately by the user. A released manufacturing test image/procedure must define tag-off current, power rails, USB enumeration, SD read/write, sensor communication and all four servo signals. No programmer/test fixture or test time is assumed to be included without an explicit line item.

## Files still required before a manufacturing-ready inquiry

1. Fully connected PCB and raw DRC report with each retained mechanical exception identified.
2. Reviewed USB pair and RP2350 power/clock routing; explicit stackup/impedance requirements.
3. Fabrication Gerbers, drills, board drawing and assembly drawings for both faces.
4. Released BOM, top/bottom centroid files and connector orientation/polarity drawing.
5. Tag-harness drawing, programming image and manufacturing acceptance procedure.

Do not send the current development PCB as a released fabrication package. A budgetary inquiry made earlier must clearly state that routing and assembly details can change its price.
