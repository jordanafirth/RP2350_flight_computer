# Undergraduate flight computer

Custom Feather-size data logger for a reusable teaching fleet: 2,000 initial units and approximately 200 replacement units per year.

- [Development plan](docs/development-plan.md)
- [Requirements and open decisions](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Candidate GPIO allocation](docs/pin-allocation.md)
- [Reference findings](docs/reference-findings.md)
- [Part selections](docs/parts-selection.md)
- [Schematic draft and review notes](docs/schematic-review.md)
- [Placement and mechanical review](docs/placement-review.md)
- [Routing development review](docs/routing-review.md)
- [Reference acquisition](references/README.md)

Status: integrated KiCad schematic and PCB routing are under development. Critical USB, processor power and IMU connections have explicit routing; the checked working PCB has 30 unconnected items. Candidate part numbers, right-angle servo headers and the compact USB/SD arrangement are defined. Routing completion, fabricator impedance confirmation, footprint and physical validation remain open. There is no manufacturing release or complete PCBA quote yet.

The current product is an RP2040 Feather Adalogger connected by Qwiic cables to BMP280 and BNO085 breakouts, powered by a small single-cell lithium-ion battery. The target combines these functions, preferably using RP2350, and adds factory-installed servo and power-control connectors.
