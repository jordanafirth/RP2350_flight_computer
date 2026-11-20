"""Extract reference footprints through KiCad's official board importer output."""
import json
import re
from pathlib import Path
import copy
import xml.etree.ElementTree as ET
from kicad_sexpr import Quoted, loads, dumps, children, first

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware' / 'rev-a'
LIB = OUT / 'FlightComputer.pretty'
LIB.mkdir(exist_ok=True)
boards = {
    'Adafruit-Feather-RP2350-PCB': 'rp2350',
    'Adafruit-Feather-RP2040-Adalogger-PCB': 'adalogger',
    'Adafruit-BNO08x-PCB': 'bno085',
    'Adafruit-BMP5xx-Temperature-and-Pressure-Sensor-PCB': 'bmp581',
}
loaded = {repo: loads((ROOT / 'hardware' / 'imports' / 'boards' / (name+'.kicad_pcb')).read_text(encoding='utf-8')) for repo, name in boards.items()}
model = json.loads((OUT / 'connectivity.json').read_text(encoding='utf-8'))
saved = set()
for part in model['parts']:
    if not part['footprint'].startswith('FlightComputer:') or part['source'] == 'Custom integration':
        continue
    repo = part['source'].split('/')[0]
    ref = part['source'].rsplit(':', 1)[1]
    matches = [fp for fp in children(loaded[repo], 'footprint') if any(prop[1] == 'Reference' and prop[2] == ref for prop in children(fp, 'property'))]
    if len(matches) != 1:
        # KiCad annotates vendor references such as "L" and "CHG" that have
        # no number. Match their original footprint/package and exact location.
        board_path = ROOT / 'references' / part['source'].rsplit(':', 1)[0].replace('.sch', '.brd')
        eagle = ET.parse(board_path).getroot().find('drawing/board')
        element = next(e for e in eagle.findall('elements/element') if e.get('name') == ref)
        ex, ey = float(element.get('x')), -float(element.get('y'))
        matches = [fp for fp in children(loaded[repo], 'footprint') if fp[1] == part['package'] and first(fp, 'at') and abs(float(first(fp, 'at')[1])-ex) < 0.0001 and abs(float(first(fp, 'at')[2])-ey) < 0.0001]
    if len(matches) != 1:
        raise ValueError(f'Cannot identify unique source footprint for {part["ref"]}: {repo} {ref}')
    name = part['footprint'].split(':', 1)[1]
    if name in saved:
        continue
    fp = copy.deepcopy(matches[0])
    fp[1] = Quoted(name)
    position = first(fp, 'at')
    angle = float(position[3]) if len(position) > 3 else 0.0
    if first(fp, 'layer')[1] == 'B.Cu':
        # The only required underside reference packages are one-pad test pads.
        # Recreate these explicitly on the component side rather than carry a
        # mirrored library footprint or board-specific text orientation.
        if len(children(fp, 'pad')) != 1:
            raise ValueError(f'Unexpected mirrored multi-pad footprint: {name}')
        pin_number = children(fp, 'pad')[0][1]
        diameter = str(first(children(fp, 'pad')[0], 'size')[1])
        fp = loads(f'(footprint {json.dumps(name)} (version 20241229) (generator "flight_computer_generator") (layer "F.Cu") (attr smd) (property "Reference" "REF**" (at 0 -2) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)))) (property "Value" {json.dumps(name)} (at 0 2) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15)))) (pad {json.dumps(pin_number)} smd circle (at 0 0) (size {diameter} {diameter}) (layers "F.Cu" "F.Mask")))')
    else:
        fp = [item for item in fp if not (isinstance(item, list) and item and item[0] in {'at', 'path', 'sheetname', 'sheetfile', 'uuid'})]
        fp.insert(2, ['version', '20241229'])
        fp.insert(3, ['generator', Quoted('flight_computer_generator')])
        for pad in children(fp, 'pad'):
            at = first(pad, 'at')
            old_angle = float(at[3]) if len(at) > 3 else 0.0
            at[:] = ['at', at[1], at[2], str(round((old_angle-angle) % 360, 6))]
        for prop in children(fp, 'property'):
            if prop[1] == 'Reference':
                prop[2] = Quoted('REF**')
            elif prop[1] == 'Value':
                prop[2] = Quoted(name)
    def clean(node):
        return [clean(child) if isinstance(child, list) else child for child in node if not (isinstance(child, list) and child and child[0] in {'uuid', 'net', 'sheetname', 'sheetfile', 'path'})]
    fp = clean(fp)
    # The imported legacy outlines cross solder lands. Keep these outlines in
    # the assembly layer; actual board silkscreen is drawn around placed parts.
    for graphic in fp:
        if isinstance(graphic,list) and graphic and graphic[0].startswith('fp_'):
            layer = first(graphic,'layer')
            if layer and layer[1] == 'F.SilkS':
                layer[1] = Quoted('F.Fab')
    if name == 'DFN2015-3':
        # Eagle's drain-land extension imports as an unnetted copper graphic.
        # Represent the identical polygon as another land of physical pad 3.
        for graphic in list(children(fp, 'fp_poly')):
            if first(graphic, 'layer')[1] != 'F.Cu':
                continue
            fp.remove(graphic)
            land = loads('(pad "3" smd custom (at 0 0) (size 0.1 0.1) (layers "F.Cu") (options (clearance outline) (anchor circle)))')
            land.append(['primitives', ['gr_poly', copy.deepcopy(first(graphic,'pts')), ['width','0'], ['fill','yes']]])
            fp.append(land)
    (LIB / (name+'.kicad_mod')).write_text(dumps(fp)+'\n', encoding='utf-8', newline='\n')
    saved.add(name)

servo = ['(footprint "Servo_RA_3x04_P2.54mm_TSW10408" (version 20260206) (generator "flight_computer_generator") (layer "F.Cu") (attr through_hole)',
         '(property "Reference" "REF**" (at 3.81 -2.54) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
         '(property "Value" "TSW-104-08-T-T-RA" (at 3.81 10.5) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
         # Samtec series print Fig. 5 / Tables 1 and 5, lead style -08:
         # same 3x4 pad matrix; body 1.52 mm forward of the nearest row,
         # 2.54-mm body depth, 5.84-mm exposed posts, 2.29-mm solder tail.
         '(fp_rect (start -1.27 6.60) (end 8.89 9.14) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
         '(fp_rect (start -1.52 -1.10) (end 9.14 15.23) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))']
for channel in range(4):
    for row in range(3):
        number = channel*3+row+1
        servo.append(f'(pad "{number}" thru_hole {"rect" if number == 1 else "circle"} (at {channel*2.54} {row*2.54}) (size 1.7 1.7) (drill 1.02) (layers "*.Cu" "*.Mask"))')
    servo.append(f'(fp_line (start {channel*2.54} 9.14) (end {channel*2.54} 14.98) (stroke (width 0.64) (type default)) (layer "F.Fab"))')
servo.append(')')
(LIB / 'Servo_RA_3x04_P2.54mm_TSW10408.kicad_mod').write_text('\n'.join(servo)+'\n', encoding='utf-8', newline='\n')
hole = loads('(footprint "MountingHole_M2_Head3.8mm" (version 20260206) (generator "flight_computer_generator") (layer "F.Cu") (descr "M2 clearance, nonconductive hardware; maximum head/standoff diameter 3.8 mm") (property "Reference" "H**" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15)))) (property "Value" "M2 / max head 3.8mm" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15)))) (attr exclude_from_bom exclude_from_pos_files) (pad "" np_thru_hole circle (at 0 0) (size 2.2 2.2) (drill 2.2) (layers "*.Cu" "*.Mask")))')
for side in ('F','B'):
    hole.append(loads(f'(fp_circle (center 0 0) (end 2.1 0) (stroke (width 0.05) (type default)) (fill none) (layer "{side}.CrtYd"))'))
(LIB/'MountingHole_M2_Head3.8mm.kicad_mod').write_text(dumps(hole)+'\n',encoding='utf-8',newline='\n')
(OUT / 'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "FlightComputer") (type "KiCad") (uri "${KIPRJMOD}/FlightComputer.pretty") (options "") (descr "Converted pinned reference footprints plus custom servo header")))\n', encoding='utf-8', newline='\n')
print(f'Saved {len(saved)} converted footprints and one custom servo-header footprint.')
