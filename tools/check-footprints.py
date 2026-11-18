"""Check source-derived footprint pad geometry against pinned Eagle packages.

This checks conversion fidelity, not suitability for an exact ordered IC or
assembler process. Newly selected standard-library parts need their own review.
"""
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from kicad_sexpr import loads, children, first

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware/rev-a'
model = json.loads((OUT/'connectivity.json').read_text(encoding='utf-8'))
checked = set()
source_pads = 0
errors = []
for part in model['parts']:
    if not part['footprint'].startswith('FlightComputer:') or part['source'] == 'Custom integration':
        continue
    name = part['footprint'].split(':', 1)[1]
    fp = loads((OUT/'FlightComputer.pretty'/(name+'.kicad_mod')).read_text(encoding='utf-8'))
    # The first land is the original pad. A later same-number land can carry
    # an imported copper extension without changing the original pad geometry.
    pads = {pad[1]: pad for pad in reversed(children(fp, 'pad')) if pad[1]}
    missing = {pin['number'] for pin in part['pins']} - set(pads)
    if missing:
        errors.append(f'{part["ref"]}: symbol pins missing from footprint: {missing}')
    if name in checked:
        continue
    checked.add(name)
    source_path, ref = part['source'].rsplit(':', 1)
    sch = ET.parse(ROOT/'references'/source_path).getroot().find('drawing/schematic')
    src_part = next(p for p in sch.findall('parts/part') if p.get('name') == ref)
    lib = next(lib for lib in sch.findall('libraries/library') if lib.get('name') == src_part.get('library'))
    package = next(p for p in lib.findall('packages/package') if p.get('name') == part['package'])
    for source in list(package.findall('smd'))+list(package.findall('pad')):
        number = source.get('name')
        if number not in pads:
            errors.append(f'{name}: source pad {number} missing')
            continue
        source_pads += 1
        pad = pads[number]
        at = first(pad, 'at')
        expected = (float(source.get('x')), -float(source.get('y')))
        if math.dist((float(at[1]),float(at[2])), expected) > 0.00001:
            errors.append(f'{name}.{number}: center differs from Eagle {expected} vs {at[1:3]}')
        if source.tag == 'smd':
            size = first(pad, 'size')
            wanted_size = float(source.get('dx')), float(source.get('dy'))
            if math.dist((float(size[1]),float(size[2])), wanted_size) > 0.00001:
                errors.append(f'{name}.{number}: SMD size differs')
            # Eagle SMD rectangles/rounded rectangles are unchanged by 180
            # degrees. KiCad may choose the equivalent opposite orientation.
            wanted_angle = -float(source.get('rot','R0').replace('R','')) % 180
            angle = float(at[3]) % 180 if len(at)>3 else 0
            if min((wanted_angle-angle)%180, (angle-wanted_angle)%180)>0.00001:
                errors.append(f'{name}.{number}: angle differs {wanted_angle} vs {angle}')
if errors:
    raise SystemExit('\n'.join(errors[:40]))
report = {'status':'pass', 'source_derived_footprints_checked':len(checked), 'source_pads_checked':source_pads, 'checks':['symbol pad-number coverage','source pad centers','source SMD pad sizes','source SMD rotations modulo 180 degrees for symmetric lands'], 'limits':'Checks conversion fidelity only. Manufacturer land patterns, selected part variants, paste/mask and mechanical clearances require independent review.'}
(ROOT/'reports/schematic/footprint-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(report,indent=2))
