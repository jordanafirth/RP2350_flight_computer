# Hardware attribution and changes

The integrated schematic and source-derived footprints incorporate Adafruit Industries open hardware designed by Limor Fried/Ladyada and Adafruit Industries, as credited in the original repositories. Retained source READMEs and license files are included under `references/` for each design:

- Adafruit Feather RP2040 Adalogger PCB.
- Adafruit Feather RP2350 PCB.
- Adafruit BNO08x PCB.
- Adafruit BMP5xx Temperature and Pressure Sensor PCB.

The historical BMP280 reference is also retained with its original notices.

Adafruit invests time and resources providing these open source designs. Please support Adafruit and open-source hardware by purchasing products from Adafruit.

Source-derived hardware is provided under Creative Commons Attribution-ShareAlike 3.0 Unported, with the full license retained in each source repository's `license.txt`. Preserve attribution, identify modifications, and carry the applicable share-alike terms when distributing derivatives.

Changes in this project include circuit integration, a custom GPIO map, shared 3.3 V sensor interfaces, removal of breakout-only voltage translation and regulation, omission of display and PSRAM features, BMP581 selection, four servo ports, and a tagged power-control connector with switched battery-voltage servo power. New schematic graphics are simplified representations with explicit physical pad numbering derived from the sources.

Adafruit has not reviewed or endorsed this custom board. It remains an unmanufactured development draft.

The PCB placement also uses standard KiCad library footprints. KiCad library material is distributed under CC BY-SA 4.0 with the KiCad Libraries Exception; see https://www.kicad.org/libraries/license/. Preserve the applicable library notices when redistributing library files.
