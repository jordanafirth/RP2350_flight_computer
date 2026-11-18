# Candidate RP2350 pin allocation

Status: draft, not a released pinout. Based on the published RP2350 Feather schematic at revision `d7bc5cb6c16f071e01ae1cf790ee2142d376ee41`; alternate functions checked against that symbol. This is not a claim that the RP2350 Adalogger uses this mapping. Verify against the selected RP2350 package/datasheet during schematic review.

| GPIO | Proposed function | Resource / note |
| --- | --- | --- |
| 0 | Exposed UART TX | Preserve Feather access; UART0 TX |
| 1 | Exposed UART RX | Preserve Feather access; UART0 RX |
| 2 | Sensor/expansion SDA | I2C1 SDA; BNO085, barometer, optional Qwiic share the bus |
| 3 | Sensor/expansion SCL | I2C1 SCL; use deliberate combined pull-up sizing |
| 4 | Exposed spare | Preserve RP2350 Feather header access |
| 5 | Servo 1 signal | PWM2 B |
| 6 | Servo 2 signal | PWM3 A |
| 7 | Status LED / exposed shared pin | Preserve RP2350 reference LED assignment if retained |
| 8 | Exposed spare | Omit optional PSRAM; no PSRAM CS needed |
| 9 | Servo 3 signal | PWM4 B |
| 10 | Servo 4 signal | PWM5 A |
| 11 | Exposed spare | Preserve Feather access |
| 12 | SD MISO / DAT0 | SPI1 RX |
| 13 | SD CS / DAT3 | SPI1 CSn, or software-controlled CS |
| 14 | SD clock | SPI1 SCK |
| 15 | SD MOSI / CMD | SPI1 TX |
| 16 | BNO085 interrupt | H_INTN, input |
| 17 | BNO085 reset | NRST, output with defined startup behavior |
| 18 | SD card detect | Optional; omit connection if selected socket lacks a detect switch |
| 19 | BMP581 interrupt | BMP_INT; BNO085 BOOTN instead has a fixed pull-up |
| 20 | Exposed SPI MISO | SPI0 RX; preserve RP2350 Feather header function |
| 21 | Addressable status LED | Preserve RP2350 reference assignment if retained; may omit LED to save power/space |
| 22 | Exposed SPI clock | SPI0 SCK |
| 23 | Exposed SPI MOSI | SPI0 TX |
| 24 | Exposed spare | Preserve Feather access |
| 25 | Exposed spare | Preserve Feather access |
| 26 | Exposed analog A0 | ADC0 |
| 27 | Exposed analog A1 | ADC1 |
| 28 | Exposed analog A2 | ADC2 |
| 29 | Exposed analog A3 | ADC3; optional battery divider would share/consume this input and is not assumed |

Dedicated pins separately serve USB, QSPI flash, SWD, reset and clocks. ENABLE is a regulator control, not one of these GPIO assignments.

## Design consequences

- Four servo signals use distinct PWM slices. Shared frequency restrictions between channels of one slice do not constrain this set.
- SD uses SPI1 and expansion uses SPI0. This avoids coupling expansion transfers and SD transfers through one hardware SPI peripheral.
- This is a conventional SPI microSD connection. It does not preserve the RP2040 Adalogger's exact SDIO pin arrangement, and is not promised to be SDIO-compatible.
- A 3.3 V I2C bus eliminates breakout-only level shifters. Preserve all sensor straps, decoupling and required auxiliary-bus pull-ups based on the sensor datasheet.
- Removing the RP2350 Feather's HSTX display connector and optional PSRAM releases internal space and GPIO. Neither is requested for this logger.
- Header pads for servo signals may be retained as shared access, with clear labels; they are not independent additional GPIO.
- Application code and any PlatformIO board definition must use the final documented custom mapping. Neither is implemented here.
