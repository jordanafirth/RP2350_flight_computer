"""Compare every native PCB pad net against the integrated circuit model."""
import argparse
import json
from pathlib import Path
from kicad_sexpr import loads,children,first
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--board',type=Path,default=ROOT/'hardware/rev-a/flight-computer.kicad_pcb')
parser.add_argument('--report',type=Path,default=ROOT/'reports/pcb/pad-net-check.json')
args=parser.parse_args()
model=json.loads((ROOT/'hardware/rev-a/connectivity.json').read_text(encoding='utf-8'))
parts={p['ref']:p for p in model['parts'] if not p['ref'].startswith('#')}
seen=set();uuids=set();errors=[];checked=0;connected=set();mechanical=[]
for fp in children(loads(args.board.read_text(encoding='utf-8')),'footprint'):
    ref=next(p[2] for p in children(fp,'property') if p[1]=='Reference')
    if ref not in parts:
        if not first(fp,'attr') or 'board_only' not in first(fp,'attr'):errors.append({'unexpected_component':ref})
        continue
    if ref in seen:errors.append({'duplicate_reference':ref})
    seen.add(ref)
    expected={}
    for pin in parts[ref]['pins']:
        prefix='' if pin['name']==pin['number'] else pin['name']+'-'
        expected[pin['number']]=pin['net'] or f'unconnected-({ref}-{prefix}Pad{pin["number"]})'
    present=set()
    for pad in children(fp,'pad'):
        number=pad[1]
        if not number:continue
        net=first(pad,'net');actual=net[1] if net else ''
        if number not in expected and not actual:
            mechanical.append({'ref':ref,'pad':number});continue
        if number not in expected or actual!=expected[number]:errors.append({'ref':ref,'pad':number,'expected':expected.get(number),'actual':actual})
        checked+=1
        if number in expected and not expected[number].startswith('unconnected-'):connected.add((ref,number))
        present.add(number)
        uid=first(pad,'uuid')
        if uid and uid[1] in uuids:errors.append({'duplicate_pad_uuid':uid[1]})
        if uid:uuids.add(uid[1])
    if present!=set(expected):errors.append({'ref':ref,'missing_pad_numbers':sorted(set(expected)-present)})
if seen!=set(parts):errors.append({'missing_components':sorted(set(parts)-seen)})
result={'status':'pass' if not errors else 'fail','board':args.board.name,'components_checked':len(seen),
        'numbered_circuit_lands_checked':checked,'connected_physical_pads_checked':len(connected),'unassigned_mechanical_lands':mechanical,'errors':errors,
        'limits':'PCB/model equivalence only. Does not validate circuit design, physical footprints, routing or fabrication.'}
args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in result.items() if k!='limits'},indent=2))
if errors:raise SystemExit(1)
