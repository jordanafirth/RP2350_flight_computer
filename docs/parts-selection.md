# Initial part selections

Updated 2026-11-19. All populated draft components now have candidate manufacturer part numbers in `hardware/rev-a/draft-bom.csv`. Package qualification, production sourcing and an assembler quote remain open.

| Function | Selected for draft | Basis / remaining review |
| --- | --- | --- |
| Processor | RP2350A, A4 stepping; order code SC1509-A4 | RP2350A0A4 is the chip marking; require the A4 order code on the quote |
| IMU | BNO085 | User's established sensor; shared BNO080 reference circuit is intentional |
| Barometer | BMP581 | 3.3 V compatible, 2 x 2 mm package; use new driver and I2C address 0x46 with SDO grounded |
| Logic regulator | RT9080-33GJ5 | Reuse Feather reference; enabled 3.3 V rail |
| Charger | MCP73831T-2ACI/OT | Reuse 4.2 V single-cell Feather charging circuit |
| Charge programming resistor R8 | 5.1 kilohm, 1%; RC0402FR-075K1L candidate | Approximately 196 mA nominal, retained from the reference and below the selected battery's 400 mA maximum |
| Battery | Adafruit PID 3898, 3.7 V, 400 mAh | User confirmed; protected battery with Adafruit-polarity JST-PH plug |
| Battery socket | S2B-PH-SM4-TB(LF)(SN) candidate | Standard Feather location on top; confirm exact land pattern and polarity against selected socket |
| Servo connector | Samtec TSW-104-08-T-T-RA | User-selected right-angle pins, cables exiting through the end; 12 pins, three rows, 2.54 mm pitch and 1.02-mm finished holes; factory installed |
| Tag socket | JST BM02B-SRSS-TB(LF)(SN) | Two-pin SH, SMT, top entry for tag access; physically distinct from the battery's PH connector. This is separate from the horizontal Qwiic requirement. |
| Tagged shorting plug | SHR-02V-S-B housing + two SSH-003T-P0.2-H contacts + short 28 AWG loop | Vendor supplies fully crimped/shorted/tagged assembly; extraction force and repeated-use endurance need pilot testing |
| Servo supply switch | TPS22919DCKR | Small switch controlled by the same ENABLE net; delivers battery voltage, without a boost converter |
| QSPI storage | Winbond W25Q64JVXGIQ | 8 MB; source USON-8 footprint retained, package review remains |
| microSD | Molex 1040310811 | Compact push-pull socket with card detection, standard KiCad footprint; underneath USB at the same end |
| Processor crystal | Abracon ABM8-272-T3 | 12 MHz, 10 pF load; manufacturer recommends it for RP2040/RP235x; case pads grounded |
| IMU crystal | Abracon ABS07-32.768KHZ-T | 32.768 kHz, 12.5 pF load; 3.2 x 1.5 mm package |
| Battery-path MOSFET | Diodes DMP2045UFY4-7 | Replaces NRND DMG3415UFY4 with manufacturer-recommended same-package alternative |
| Optional RGB LED D5 | SK6805-EC15, DNP | Manufacturer minimum supply exceeds the 3.3 V rail. Exclude from assembled quote; retain the optional footprint and GPIO |
| USB-C | GCT USB4110-GF-A | All-SMT shell avoids shell tails beneath the PCB in the overlapping USB/SD placement; verify locating-peg clearance against socket drawing |
| Expansion | Existing header pads and one horizontal Qwiic socket, JST SM04B-SRSS-TB(LF)(SN) candidate | Retain side entry, source footprint JST_SH4_RA, and cable access; no HSTX/display connector and no optional PSRAM |

## Sources for electrical selections

- [BMP581 manufacturer specifications](https://www.bosch-sensortec.com/en/products/environmental-sensors/pressure-sensors/bmp581) and [datasheet](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp581-ds004.pdf).
- [Battery PID 3898 specifications](https://www.adafruit.com/product/3898): charge at 400 mA or less; approximate body 36 x 17 x 7.8 mm. These published dimensions are a starting envelope, not manufacturing tolerances.
- [MCP73831 datasheet](https://www.microchip.com/content/dam/mchp/documents/APID/ProductDocuments/DataSheets/MCP73831-Family-Data-Sheet-DS20001984H.pdf): programming relation approximately 1,000 / RPROG(kilohms) mA. For 5.1 kilohms this is about 196 mA, or 0.49 C for 400 mAh.
- [RT9080 datasheet](https://www.richtek.com/assets/product_file/RT9080/DS9080-08.pdf).
- [TPS22919 datasheet](https://www.ti.com/lit/ds/symlink/tps22919.pdf): switch control and physical pin assignment reviewed for the draft.
- [Samtec right-angle servo header](https://www.samtec.com/products/tsw-104-08-t-t-ra), [manufacturer print](https://suddendocs.samtec.com/prints/tsw-xxx-xx-xxx-x-xx-xxx-mkt.pdf), and [JST SH family drawing](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf).
- [SC1509-A4 orderable part](https://www.digikey.com/en/products/detail/raspberry-pi/SC1509-A4/26241108), [Molex socket](https://www.molex.com/en-us/products/part-detail/1040310811), [12-MHz crystal](https://abracon.com/datasheets/ABM8-272-T3.pdf), and [32.768-kHz crystal](https://abracon.com/Resonators/ABS07.pdf).
- [DMP2045UFY4 datasheet](https://www.diodes.com/_files/datasheets/DMP2045UFY4.pdf) and [RGB LED supply limits](https://cdn-shop.adafruit.com/product-files/4492/Datasheet.pdf).
- [GCT USB4110](https://gct.co/connector/usb4110): horizontal USB 2.0 Type-C with SMT shell stakes. Its soldered shell differs from the through-hole-stake USB4105 assessed earlier.

## Procurement observations

Prices and stock below are public-page observations retrieved on 2026-11-18, not live supplier commitments. No order or reservation was placed.

| Item | Listing evidence | Implication |
| --- | --- | --- |
| BNO085 | [Mouser listing](https://www.mouser.com/en/ProductDetail/Ceva/BNO085?qs=ulEaXIWI0c9BFVeZDQCmmQ%3D%3D) showed approximately 10,000 available and $8.70 each at 2,000 | Plausible initial supply route; obtain current quote before committing |
| BMP581 | [DigiKey listing](https://www.digikey.com/en/products/detail/bosch-sensortec/BMP581/16036134) returned differing cached stock counts across variants; [Mouser search](https://www.mouser.com/en/c/?q=BMP581) showed backorder, $2.18 at 2,000 | Exact immediately available quantity is unconfirmed. Do not mark production sourcing complete based on search results |
| BMP390 | [Mouser listing](https://www.mouser.com/en/ProductDetail/Bosch-Sensortec/BMP390?qs=QNEnbhJQKvYQVfvRMgo2YA%3D%3D) showed zero stock and incoming 2027 quantities | Less attractive initial sourcing evidence than a presumed readily available replacement |
| TSW-104-08-T-T-RA | Samtec product page observed 2026-11-19 showed $0.398 at 2,000 and a 2,083-piece availability figure | Confirm the right-angle variant, delivery and assembly handling in the quote |

Do not infer a complete board price by adding these few lines. PCB fabrication, all remaining components, programming, test, yield allowance, tags, batteries, freight and assembly are not quoted.
