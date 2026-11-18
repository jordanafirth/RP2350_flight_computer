# Upstream design references

These are reference inputs, not the custom flight computer. Keep vendor CAD unmodified. Acquisition records belong in `manifest.json`; generated inspection results belong in `reports/`.

Sources to retrieve:

- https://github.com/adafruit/Adafruit-Feather-RP2040-Adalogger-PCB
- https://github.com/adafruit/Adafruit-Feather-RP2350-PCB (standard HSTX Feather, not the Adalogger)
- https://github.com/adafruit/Adafruit-BNO08x-PCB
- https://github.com/adafruit/Adafruit-BMP280-Breakout-PCB (historical circuit reference)
- https://github.com/adafruit/Adafruit-BMP5xx-Temperature-and-Pressure-Sensor-PCB (BMP581 sensor core for the new draft)

The specific RP2350 Adalogger CAD has not yet been located and verified. Evidence of development does not establish that editable hardware files are published:

- https://blog.adafruit.com/?p=630120
- https://circuitpython.org/board/adafruit_feather_rp2350_adalogger/

Engineering references already checked in the conversation:

- RP2350 A4 silicon update: https://www.raspberrypi.com/news/rp2350-a4-rp2354-and-a-new-hacking-challenge/
- BMP280 discontinuation statement: https://community.bosch-sensortec.com/mems-sensors-forum-jrmujtaw/post/bosch-official-bmp280-c-language-driver-api-link-issue-29nynRBP64lzoqf
- Candidate BMP390: https://www.bosch-sensortec.com/en/products/environmental-sensors/pressure-sensors/bmp390
- BNO08x datasheet: https://www.ceva-ip.com/wp-content/uploads/BNO080_085-Datasheet.pdf

## Acquisition

Run `tools/fetch-references.ps1` from PowerShell with network access. It selects source CAD and license/readme files from pinned GitHub revisions; it does not install software, modify upstream, or order hardware. After a first successful acquisition, it reuses the revisions in the manifest. Downloads include SHA-256 hashes for traceability. License terms must be reviewed before distributing derivatives.
