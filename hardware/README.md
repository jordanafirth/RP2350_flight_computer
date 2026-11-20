# Hardware work in progress

`imports/` contains local, ignored intermediate vendor conversions, not the custom board. In particular, the reference RP2350 Feather includes an HSTX display connector that is explicitly excluded from the custom design. The rebuild script regenerates its required board conversions from pinned sources.

`rev-a/flight-computer.kicad_pro` is the integrated custom schematic project, with a local symbol library and footprint library. It is a development draft and must not be sent for manufacturing.

`rev-a/flight-computer.kicad_pcb` contains an incomplete routing candidate. USB and underside microSD occupy the same short end; four right-angle servo ports occupy the opposite end. The retained Qwiic connector is horizontal. The battery socket remains on top in the reference Feather location. Reports in `reports/pcb/` are named development checkpoints, with unresolved connections and raw violations retained. Mechanical review and remaining release gates are in `docs/placement-review.md`.

Upstream Adafruit-derived circuits retain the attribution and CC BY-SA 3.0 notices in `references/`. Changes include integration, connector changes, GPIO reassignment and removal of breakout-only interfaces. No Adafruit endorsement is implied.

## Rebuilding

After reference acquisition, run `tools/rebuild-hardware.ps1`. It uses an existing KiCad CLI and Python interpreter; optional `-KiCadCli` and `-Python` parameters override discovery. Schematic generation and checks use the Python standard library. Placement, metadata synchronization and routing interchange require KiCad's bundled Python with `pcbnew` and `wx`; they initialize KiCad's native project API without opening the editor.

Generation overwrites the custom draft from the model in `tools/build-draft-schematic.py`. If editing the native CAD manually, first preserve the edits and reconcile them into the generator before running it again.

Run `tools/place-pcb.py` after rebuilding the schematic and footprints to regenerate the placement; this also overwrites the PCB. It uses the local KiCad footprint libraries in addition to the converted project library. Do not run it over a manually routed board without preserving and reconciling those changes.

See [review notes](../docs/schematic-review.md) and [hardware attribution](NOTICE.md).

## Checking and routing

`tools/check-hardware.ps1` runs the current schematic and PCB checks without regenerating the PCB. Its `-PreviewOnly` option renders cropped top/bottom engineering views. Always inspect the raw DRC results; successful report generation does not mean a clean board.

`tools/route-board.py` provides native KiCad DSN/SES interchange. Use KiCad's bundled Python. Exporting with `--fresh-routing` omits existing tracks from the routing input; importing with `--replace-tracks` replaces candidate tracks and requires a prior backup. `--three-signal-layers` leaves L2 as ground reference and allows L3 routing.

`tools/run-router.ps1` runs the locally verified Freerouting 2.0.1 library through `tools/RouteBoard.java`, with an explicit pass limit and synchronous SES export. The upstream 2.0.1 CLI scheduler did not honor the requested routing stop and could race SES serialization; do not use its normal CLI entry point for this project. The wrapper starts no GUI, API server or analytics. Routing output still requires independent KiCad checks and engineering review.
