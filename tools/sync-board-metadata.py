"""Update quoted values/MPNs/DNP flags without regenerating placed/routed copper."""
import json
import copy
from pathlib import Path
from kicad_sexpr import Quoted,loads,dumps,children,first
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/rev-a'
parts={p['ref']:p for p in json.loads((OUT/'connectivity.json').read_text())['parts'] if not p['ref'].startswith('#')}
path=OUT/'flight-computer.kicad_pcb'
board=loads(path.read_text(encoding='utf-8'))
seen=set()
for fp in children(board,'footprint'):
    props={p[1]:p for p in children(fp,'property')}
    ref=props['Reference'][2]
    if ref not in parts:continue
    p=parts[ref];seen.add(ref)
    if fp[1]!=p['footprint']:
        # The approved right-angle servo header retains the same electrical
        # lands. Update its body/overhang and recommended drill without moving
        # pads or invalidating routes to those pads.
        if ref!='JSERVO1' or fp[1]!='FlightComputer:Servo_3x04_P2.54mm':
            raise ValueError('Footprint mismatch: '+ref)
        new=loads((OUT/'FlightComputer.pretty'/ (p['footprint'].split(':')[1]+'.kicad_mod')).read_text())
        old_pads={pad[1]:pad for pad in children(fp,'pad')}
        new_pads={pad[1]:pad for pad in children(new,'pad')}
        if set(old_pads)!=set(new_pads):raise ValueError('Servo pad set changed')
        for num,pad in old_pads.items():
            np=new_pads[num]
            for field in ('at','size'):
                if [float(v) for v in first(pad,field)[1:3]]!=[float(v) for v in first(np,field)[1:3]]:
                    raise ValueError('Servo land geometry changed: '+num)
            first(pad,'drill')[1:]=first(np,'drill')[1:]
        fp[:]=[n for n in fp if not (isinstance(n,list) and str(n[0]).startswith('fp_'))]
        fp.extend(copy.deepcopy(n) for n in new if isinstance(n,list) and str(n[0]).startswith('fp_'))
        fp[1]=Quoted(p['footprint'])
    props['Value'][2]=Quoted(p['value'])
    props['MPN'][2]=Quoted(p['mpn'])
    attr=first(fp,'attr')
    if attr is None:attr=['attr'];fp.append(attr)
    if 'dnp' in attr:attr.remove('dnp')
    if p['dnp']:attr.append('dnp')
if seen!=set(parts):raise ValueError('Component set mismatch; regenerate/reconcile placement instead.')
path.write_text(dumps(board)+'\n',encoding='utf-8',newline='\n')
print('Synchronized values, MPNs and DNP attributes; copper/geometry retained.')
