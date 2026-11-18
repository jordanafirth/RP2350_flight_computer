# Undergraduate flight computer

Custom Feather-size data logger for a reusable teaching fleet: 2,000 initial units and approximately 200 replacement units per year.

- [Development plan](docs/development-plan.md)
- [Requirements and open decisions](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Candidate GPIO allocation](docs/pin-allocation.md)
- [Reference findings](docs/reference-findings.md)
- [Reference acquisition](references/README.md)

Status: requirements baseline and initial reference-design audit complete; architecture, exact part selection and pin allocation underway. No custom schematic, PCB layout, or manufacturing release exists yet.

The current product is an RP2040 Feather Adalogger connected by Qwiic cables to BMP280 and BNO085 breakouts, powered by a small single-cell lithium-ion battery. The target combines these functions, preferably using RP2350, and adds factory-installed servo and power-control connectors.
