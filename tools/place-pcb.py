"""Create an unrouted native PCB placement from the integrated net model.

Coordinates in PLACEMENT are millimetres in the Feather reference coordinate
system (origin at lower left). This is a placement intermediate, not a release.
"""
import copy
import json
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from kicad_sexpr import Quoted as Q, loads, dumps, children, first
from native_cad import pcbnew, load_board, save_board

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware/rev-a'
KICAD = Path.home() / 'AppData/Local/Programs/KiCad/10.0/share/kicad'
NS = uuid.UUID('95e42019-75b7-4964-b47d-4e0c293e84bb')
def uid(key):
    return str(uuid.uuid5(NS, key))

# x, y, rotation in KiCad degrees, component face.
PLACEMENT = {
    'JSERVO1': (41.4, 7.62, 90, 'F'),
    'SW1': (42.5, 4.3, 180, 'F'),
    'JSD1': (6.4, 11.43, 270, 'B'),
    'R8': (21, 19, 0, 'B'),
    'D1': (4, 18, 90, 'F'), 'D2': (45, 18.5, 0, 'F'),
    'C2': (12.8, 11.6, 90, 'F'), 'C3': (12.8, 8.6, 270, 'F'),
    'C4': (15.4, 14.5, 0, 'B'), 'C14': (18.2, 11.9, 180, 'F'),
    'R6': (18.2, 10.314, 0, 'F'), 'R21': (30.5, 7, 0, 'B'),
    'R4': (16, 6, 180, 'B'), 'R12': (10, 6.5, 180, 'F'),
    'R9': (28, 11.11, 180, 'F'), 'R10': (28, 12.36, 180, 'F'),
    'U3': (10.4, 9.46, 90, 'F'),
    'Y1': (15.3, 9.8, 90, 'F'), 'C18': (18.1, 8.2, 90, 'F'),
    'JQT1': (36, 10.35, 180, 'F'),
    'R16': (34.5, 6.5, 0, 'F'), 'R17': (36.5, 6.5, 0, 'F'),
    'U5': (24, 11, 0, 'B'), 'U6': (33, 17, 0, 'B'),
    'Y2': (23, 15.5, 0, 'B'),
    'C31': (20, 11, 90, 'B'), 'C32': (24, 7, 0, 'B'),
    'C33': (20.5, 17.5, 0, 'B'), 'C34': (24.5, 17.5, 0, 'B'),
    'C35': (28, 11, 90, 'B'),
    'R41': (20, 8, 90, 'B'), 'R42': (18.8, 15.2, 90, 'B'),
    'R43': (28, 8, 90, 'B'), 'R44': (28, 14, 90, 'B'),
    'R45': (28, 17, 90, 'B'),
    'C36': (33, 14, 0, 'B'), 'C37': (33, 19, 0, 'B'),
    'R31': (18, 5, 90, 'B'), 'R32': (21, 5, 90, 'B'),
    'R33': (24, 5, 90, 'B'), 'R34': (27, 5, 90, 'B'),
    'R35': (30, 5, 90, 'B'), 'R36': (33, 5, 90, 'B'),
    'C38': (18.5, 8, 90, 'B'),
    'JTAG1': (35.5, 17, 0, 'F'),
    'R51': (38, 6, 90, 'B'), 'R52': (38, 9, 90, 'B'),
    'R53': (38, 12, 90, 'B'), 'R54': (38, 15, 90, 'B'),
    'U7': (34, 10, 0, 'B'), 'R55': (34, 7, 0, 'B'),
    'C39': (34, 12.5, 0, 'B'), 'C40': (31, 10, 90, 'B'),
    'TP3': (30, 19, 0, 'B'), 'TP4': (30, 13, 0, 'B'),
    'TP5': (30, 15, 0, 'B'),
}

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
    overrides_path = OUT/'placement-overrides.json'
    overrides = json.loads(overrides_path.read_text(encoding='utf-8')) if overrides_path.exists() else {}
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
        if ref in overrides:
            x,y = overrides[ref]['x'],overrides[ref]['y']
        lib, name = part['footprint'].split(':', 1)
        path = OUT/'FlightComputer.pretty'/(name+'.kicad_mod') if lib == 'FlightComputer' else KICAD/'footprints'/(lib+'.pretty')/(name+'.kicad_mod')
        fp = loads(path.read_text(encoding='utf-8'))
        fp[:] = [n for n in fp if not (isinstance(n, list) and n[0] in {'version','generator','model','at','uuid','path'})]
        fp[1] = Q(part['footprint'])
        fp.append(loads(f'(property "MPN" {json.dumps(part["mpn"])} (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15))))'))
        # Load the library geometry at its neutral origin. Native KiCad code
        # below performs placement, pad rotations, layer flips and text mirroring.
        fp.insert(3, ['at', '0', '0', '0'])
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
    # M2 holes retain Feather X spacing. Move the Y rows outward by 0.4 mm to
    # clear the end-facing connector lands and the specified mounting hardware.
    for i,(x,y) in enumerate([(2.54,2.14),(2.54,20.72),(48.26,2.14),(48.26,20.72)],1):
        hole = loads((OUT/'FlightComputer.pretty/MountingHole_M2_Head3.8mm.kicad_mod').read_text(encoding='utf-8'))
        hole[:] = [n for n in hole if not (isinstance(n,list) and n[0] in {'version','generator','generator_version','attr','at','uuid'})]
        hole[1] = Q('FlightComputer:MountingHole_M2_Head3.8mm')
        hole.insert(3,['at',str(100+x),str(122.86-y)])
        hole.extend([['uuid',Q(uid('hole'+str(i)))],['attr','board_only','exclude_from_pos_files','exclude_from_bom']])
        for prop in children(hole,'property'):
            if prop[1]=='Reference':prop[2]=Q('H'+str(i));prop.append(['hide','yes'])
            elif prop[1]=='Value':prop.append(['hide','yes'])
        board.append(hole)
    for text,x,y in [('USB + SD',2,24.5),('4 SERVO PORTS',39,24.5),('UNROUTED PLACEMENT — NOT FOR FABRICATION',0,-3)]:
        board.append(loads(f'(gr_text {json.dumps(text)} (at {100+x} {122.86-y}) (layer "Dwgs.User") (effects (font (size 1 1) (thickness 0.15)) (justify left)))'))
    # Battery envelope below the PCB: dimensions from the PID3898 product page.
    board.append(loads('(gr_rect (start 107.4 102.93) (end 143.4 119.93) (stroke (width 0.15) (type dash)) (fill none) (layer "Dwgs.User"))'))
    board.append(['embedded_fonts','no'])
    target = OUT/'flight-computer.kicad_pcb'
    target.write_text(dumps(board)+'\n',encoding='utf-8',newline='\n')
    native = load_board(target)
    by_ref = {p['ref']:p for p in placements}
    for fp in native.GetFootprints():
        if fp.GetReference() not in by_ref:
            continue
        p = by_ref[fp.GetReference()]
        if p['side'] == 'B':
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(p['rotation'])
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100+p['x']),pcbnew.FromMM(122.86-p['y'])))
        # References belong on the assembly drawing; connector/function legends
        # are added independently on silkscreen after physical placement is fixed.
        fp.Reference().SetLayer(pcbnew.B_Fab if p['side'] == 'B' else pcbnew.F_Fab)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(.8),pcbnew.FromMM(.8)))
        fp.Reference().SetTextThickness(pcbnew.FromMM(.12))
    save_board(native,target)
    report = ROOT/'reports/pcb'; report.mkdir(parents=True,exist_ok=True)
    (report/'placement.json').write_text(json.dumps({'status':'unrouted placement; package and clearance review pending','outline_mm':[50.8,22.86],'battery_envelope_mm':[36,17,7.8],'placements':placements},indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Placed {len(placements)} schematic items and four mounting holes; no routing generated.')

if __name__ == '__main__':
    main()
