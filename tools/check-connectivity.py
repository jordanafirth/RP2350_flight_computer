"""Compare KiCad's independently exported netlist with the draft connection model."""
import collections
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
model = json.loads((ROOT / 'hardware/rev-a/connectivity.json').read_text(encoding='utf-8'))
netlist = ET.parse(ROOT / 'reports/schematic/flight-computer.net.xml').getroot()
expected = {}
for part in model['parts']:
    if part['ref'].startswith('#'):
        continue
    for pin in part['pins']:
        if pin['net'] is not None:
            expected[(part['ref'], pin['number'])] = pin['net']
actual = {}
for net in netlist.findall('nets/net'):
    for node in net.findall('node'):
        key = node.get('ref'), node.get('pin')
        if key in actual:
            raise ValueError(f'Pad appears on multiple nets: {key}')
        actual[key] = net.get('name')
errors = []
for key, wanted in expected.items():
    if actual.get(key) != wanted:
        errors.append(f'{key}: expected {wanted}, got {actual.get(key)}')
for key in actual:
    if key not in expected and not actual[key].startswith('unconnected-'):
        errors.append(f'Unexpected netlisted pad: {key} on {actual[key]}')
component_refs = {x.get('ref') for x in netlist.findall('components/comp')}
expected_refs = {x['ref'] for x in model['parts'] if not x['ref'].startswith('#')}
if component_refs != expected_refs:
    errors.append(f'Component mismatch: missing {expected_refs-component_refs}; extra {component_refs-expected_refs}')
if 'CN2' in component_refs or any('FPC' in p['package'] for p in model['parts']):
    errors.append('Unrequested display connector is present')

# Hardware requirements checked separately from whole-model equivalence.
requirements = {
    ('JTAG1','1'): 'ENABLE', ('JTAG1','2'): 'GND',
    ('U5','19'): 'SCL', ('U5','20'): 'SDA', ('U5','14'): 'BNO_INT_N', ('U5','11'): 'BNO_RESET_N',
    ('U6','2'): 'SCL', ('U6','4'): 'SDA', ('U6','5'): 'GND', ('U6','7'): 'BMP_INT',
    ('U7','1'): 'VBAT', ('U7','3'): 'ENABLE', ('U7','6'): 'VBAT_SERVO',
}
for channel in range(4):
    requirements[('JSERVO1',str(channel*3+1))] = f'SERVO{channel+1}'
    requirements[('JSERVO1',str(channel*3+2))] = 'VBAT_SERVO'
    requirements[('JSERVO1',str(channel*3+3))] = 'GND'
for key, wanted in requirements.items():
    if actual.get(key) != wanted:
        errors.append(f'Requirement check failed: {key} expected {wanted}')
if errors:
    raise SystemExit('\n'.join(errors[:40]))
report = {'status':'pass', 'components':len(component_refs), 'connected_physical_pads_checked':len(expected), 'hardware_requirement_checks':len(requirements), 'display_connector_present':False, 'limits':'Export/model equivalence and named hardware connections only; does not establish physical footprint correctness or circuit performance.'}
(ROOT / 'reports/schematic/connectivity-check.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
print(json.dumps(report, indent=2))
