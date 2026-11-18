# Undergraduate flight computer

Custom Feather-size data logger for a reusable teaching fleet: 2,000 initial units and approximately 200 replacement units per year.

- [Development plan](docs/development-plan.md)
- [Requirements and open decisions](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Candidate GPIO allocation](docs/pin-allocation.md)
- [Reference findings](docs/reference-findings.md)
- [Part selections](docs/parts-selection.md)
- [Schematic draft and review notes](docs/schematic-review.md)
- [Reference acquisition](references/README.md)

Status: integrated KiCad schematic and initial native PCB placement generated. The PCB is unrouted, with clearance, footprint and mechanical review still open. There is no manufacturing release or complete PCBA quote yet.

The current product is an RP2040 Feather Adalogger connected by Qwiic cables to BMP280 and BNO085 breakouts, powered by a small single-cell lithium-ion battery. The target combines these functions, preferably using RP2350, and adds factory-installed servo and power-control connectors.
