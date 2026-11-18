"""Create an unrouted native PCB placement from the integrated net model.

Coordinates in PLACEMENT are millimetres in the Feather reference coordinate
system (origin at lower left). This is a placement intermediate, not a release.
"""
import copy
import json
import math
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from kicad_sexpr import Quoted as Q, loads, dumps, children, first

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware/rev-a'
KICAD = Path.home() / 'AppData/Local/Programs/KiCad/10.0/share/kicad'
NS = uuid.UUID('95e42019-75b7-4964-b47d-4e0c293e84bb')
def uid(key):
    return str(uuid.uuid5(NS, key))

# x, y, rotation in KiCad degrees, component face.
PLACEMENT = {
    'JSERVO1': (41.4, 7.62, 90, 'F'),
    'JSD1': (8.3, 11.43, 270, 'B'),
    'R8': (21, 19, 0, 'B'),
    'D1': (4, 18, 90, 'F'), 'D2': (47, 18.3, 0, 'F'),
    'C2': (12.81, 10.6934, 90, 'F'), 'C3': (12.81, 8.8646, 270, 'F'),
    'R9': (18, 11.5, 0, 'B'), 'R10': (18, 13.0, 0, 'B'),
    'U3': (10.4, 9.46, 90, 'F'),
    'JQT1': (36, 10.35, 180, 'F'),
    'R16': (34.5, 6.5, 0, 'F'), 'R17': (36.5, 6.5, 0, 'F'),
    'U5': (24, 11, 0, 'B'), 'U6': (33, 17, 0, 'B'),
    'Y2': (22, 16.5, 0, 'B'),
    'C31': (20, 11, 90, 'B'), 'C32': (24, 7, 0, 'B'),
    'C33': (19, 16.5, 90, 'B'), 'C34': (25, 16.5, 90, 'B'),
    'C35': (28, 11, 90, 'B'),
    'R41': (20, 8, 90, 'B'), 'R42': (20, 14, 90, 'B'),
    'R43': (28, 8, 90, 'B'), 'R44': (28, 14, 90, 'B'),
    'R45': (28, 17, 90, 'B'),
    'C36': (33, 14, 0, 'B'), 'C37': (33, 19, 0, 'B'),
    'R31': (18, 5, 90, 'B'), 'R32': (21, 5, 90, 'B'),
    'R33': (24, 5, 90, 'B'), 'R34': (27, 5, 90, 'B'),
    'R35': (30, 5, 90, 'B'), 'R36': (33, 5, 90, 'B'),
    'C38': (17.5, 8, 90, 'B'),
    'JTAG1': (35.5, 17, 0, 'F'),
    'R51': (38, 6, 90, 'B'), 'R52': (38, 9, 90, 'B'),
    'R53': (38, 12, 90, 'B'), 'R54': (38, 15, 90, 'B'),
    'U7': (34, 10, 0, 'B'), 'R55': (34, 7, 0, 'B'),
    'C39': (34, 12.5, 0, 'B'), 'C40': (31, 10, 90, 'B'),
    'TP1': (17, 17, 0, 'B'), 'TP2': (17, 19, 0, 'B'),
    'TP3': (30, 19, 0, 'B'), 'TP4': (30, 13, 0, 'B'),
    'TP5': (30, 15, 0, 'B'),
}

def transform_fp(node, angle, bottom):
    """Flip local X for the back, then set absolute text/pad orientations."""
    for item in node:
        if not isinstance(item, list) or not item:
            continue
        if item[0] in {'at', 'start', 'end', 'mid', 'center', 'xy'} and len(item) >= 3:
            if bottom:
                item[1] = str(-float(item[1]))
            if item[0] == 'at':
                a = float(item[3]) if len(item) > 3 else 0
                item[:] = item[:3] + [str((angle + (-a if bottom else a)) % 360)]
        elif item[0] in {'layer', 'layers'} and bottom:
            for i in range(1, len(item)):
                if isinstance(item[i], str) and item[i].startswith('F.'):
                    item[i] = Q('B.' + item[i][2:])
        else:
            transform_fp(item, angle, bottom)

def main():
    model = json.loads((OUT/'connectivity.json').read_text(encoding='utf-8'))
    source = loads((ROOT/'hardware/imports/boards/rp2350.kicad_pcb').read_text(encoding='utf-8'))
    board = ['kicad_pcb', ['version', '20260206'], ['generator', Q('flight_computer_placement')],
             ['general', ['thickness', '1.6']], ['paper', Q('A4')]]
    layers = copy.deepcopy(first(source, 'layers'))
    layers.insert(2, ['4', Q('In1.Cu'), 'power'])
    layers.insert(3, ['6', Q('In2.Cu'), 'signal'])
    board.extend([layers, ['setup', ['pad_to_mask_clearance', '0']]])
    eagle = ET.parse(ROOT/'references/Adafruit-Feather-RP2350-PCB/Adafruit Feather RP2350.brd').getroot()
    elements = {e.get('name'): e for e in eagle.findall('drawing/board/elements/element')}
    placements = []
    for part in model['parts']:
        ref = part['ref']
        if ref.startswith('#'):
            continue
        if ref in PLACEMENT:
            x, y, angle, side = PLACEMENT[ref]
        else:
            if not part['source'].startswith('Adafruit-Feather-RP2350-PCB/'):
                raise ValueError('Missing placement: ' + ref)
            e = elements[part['source'].split(':')[-1]]
            x, y, angle, side = float(e.get('x')), float(e.get('y')), float(e.get('rot', 'R0').replace('MR','').replace('R','')), 'F'
        lib, name = part['footprint'].split(':', 1)
        path = OUT/'FlightComputer.pretty'/(name+'.kicad_mod') if lib == 'FlightComputer' else KICAD/'footprints'/(lib+'.pretty')/(name+'.kicad_mod')
        fp = loads(path.read_text(encoding='utf-8'))
        fp[:] = [n for n in fp if not (isinstance(n, list) and n[0] in {'version','generator','model','at','uuid','path'})]
        fp[1] = Q(part['footprint'])
        fp.append(loads(f'(property "MPN" {json.dumps(part["mpn"])} (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15))))'))
        transform_fp(fp, angle, side == 'B')
        # KiCad resolves pad angles while parsing. Parent placement must precede
        # pads, otherwise a later parent rotation rotates their angles twice.
        fp.insert(3, ['at', str(100+x), str(122.86-y), str(angle)])
        fp.extend([['uuid', Q(uid('pcb-'+ref))],
                   ['path', Q('/'+uid('root')+'/'+uid('sheet-'+part['page'])+'/'+uid('part-'+ref))]])
        for prop in children(fp, 'property'):
            if prop[1] in {'Reference','Value'}:
                prop[2] = Q(ref if prop[1] == 'Reference' else part['value'])
            if prop[1] != 'Reference':
                prop.append(['hide','yes'])
        pins = {p['number']:p for p in part['pins']}
        for pad in children(fp, 'pad'):
            pin = pins.get(str(pad[1]))
            # The upstream two-terminal crystal symbol deliberately leaves
            # its two case lands unmapped. Exact crystal selection is pending.
            mechanical = (ref == 'Y1' and str(pad[1]) in {'2','4'}) or (ref == 'JTAG1' and str(pad[1]) == 'MP')
            if pin is None and str(pad[1]) and not mechanical:
                raise ValueError(f'Unexpected physical pad {ref}.{pad[1]}')
            if pin:
                # KiCad gives explicitly unconnected symbol pins unique net
                # names; carry those through so parity checks can compare them.
                name = '' if pin['name'] == pin['number'] else pin['name']+'-'
                net = pin['net'] or f'unconnected-({ref}-{name}Pad{pin["number"]})'
                pad.append(['net',Q(net)])
            pad.append(['uuid',Q(uid(f'pad-{ref}-{pad[1]}-{len(board)}-{children(fp,"pad").index(pad)}'))])
        if part['dnp'] or ref.startswith('TP'):
            attr = first(fp, 'attr')
            if attr is None:
                attr = ['attr']; fp.append(attr)
            if part['dnp']: attr.append('dnp')
            if ref.startswith('TP'): attr.append('exclude_from_bom')
        board.append(fp)
        placements.append({'ref':ref,'x':x,'y':y,'rotation':angle,'side':side,'footprint':part['footprint']})
    for n in children(source,'gr_line') + children(source,'gr_arc'):
        if first(n,'layer')[1] != 'Edge.Cuts':
            continue
        n = copy.deepcopy(n)
        for key in ['start','mid','end']:
            point = first(n,key)
            if point:
                point[1],point[2] = str(float(point[1])+100), str(float(point[2])+122.86)
        board.append(n)
    # Four unplated 2.5-mm mounting holes. Preserve the Feather locations.
    for i,(x,y) in enumerate([(2.54,2.54),(2.54,20.32),(48.26,2.54),(48.26,20.32)],1):
        board.append(loads(f'(footprint "MountingHole:MountingHole_2.5mm" (layer "F.Cu") (at {100+x} {122.86-y}) (uuid "{uid("hole"+str(i))}") (property "Reference" "H{i}" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1)))) (attr board_only exclude_from_pos_files exclude_from_bom) (pad "" np_thru_hole circle (at 0 0) (size 2.5 2.5) (drill 2.5) (layers "*.Cu" "*.Mask")))'))
    for text,x,y in [('USB + SD',2,24.5),('4 SERVO PORTS',39,24.5),('UNROUTED PLACEMENT — NOT FOR FABRICATION',0,-3)]:
        board.append(loads(f'(gr_text {json.dumps(text)} (at {100+x} {122.86-y}) (layer "Dwgs.User") (effects (font (size 1 1) (thickness 0.15)) (justify left)))'))
    # Battery envelope below the PCB: dimensions from the PID3898 product page.
    board.append(loads('(gr_rect (start 107.4 102.93) (end 143.4 119.93) (stroke (width 0.15) (type dash)) (fill none) (layer "Dwgs.User"))'))
    board.append(['embedded_fonts','no'])
    (OUT/'flight-computer.kicad_pcb').write_text(dumps(board)+'\n',encoding='utf-8',newline='\n')
    report = ROOT/'reports/pcb'; report.mkdir(parents=True,exist_ok=True)
    (report/'placement.json').write_text(json.dumps({'status':'unrouted placement; package and clearance review pending','outline_mm':[50.8,22.86],'battery_envelope_mm':[36,17,7.8],'placements':placements},indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Placed {len(placements)} schematic items and four mounting holes; no routing generated.')

if __name__ == '__main__':
    main()
