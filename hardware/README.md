# Hardware work in progress

`imports/` contains local, ignored intermediate vendor conversions, not the custom board. In particular, the reference RP2350 Feather includes an HSTX display connector that is explicitly excluded from the custom design. The rebuild script regenerates its required board conversions from pinned sources.

`rev-a/flight-computer.kicad_pro` is the integrated custom schematic project, with a local symbol library and footprint library. It is a development draft and must not be sent for manufacturing.

`rev-a/flight-computer.kicad_pcb` is the initial, unrouted component placement. USB and underside microSD are being assessed at the same short end; four servo ports occupy the opposite end. The retained Qwiic connector is horizontal. The battery socket remains on top in the reference Feather location. See `reports/pcb/placement-drc.json` for outstanding issues, including unconnected pads; this is not a passed DRC report.

Upstream Adafruit-derived circuits retain the attribution and CC BY-SA 3.0 notices in `references/`. Changes include integration, connector changes, GPIO reassignment and removal of breakout-only interfaces. No Adafruit endorsement is implied.

## Rebuilding

After reference acquisition, run `tools/rebuild-hardware.ps1`. It uses an existing KiCad CLI and Python interpreter; optional `-KiCadCli` and `-Python` parameters override discovery. The scripts use the Python standard library and do not require the GUI or third-party Python packages.

Generation overwrites the custom draft from the model in `tools/build-draft-schematic.py`. If editing the native CAD manually, first preserve the edits and reconcile them into the generator before running it again.

Run `tools/place-pcb.py` after rebuilding the schematic and footprints to regenerate the placement; this also overwrites the PCB. It uses the local KiCad footprint libraries in addition to the converted project library. Do not run it over a manually routed board without preserving and reconciling those changes.

See [review notes](../docs/schematic-review.md) and [hardware attribution](NOTICE.md).
