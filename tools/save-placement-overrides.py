"""Preserve checked native coordinates, rotations and faces for regeneration."""
import argparse
import json
from pathlib import Path
from kicad_sexpr import loads,children,first
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--board',type=Path,default=ROOT/'hardware/rev-a/flight-computer.kicad_pcb')
parser.add_argument('--output',type=Path,default=ROOT/'hardware/rev-a/placement-overrides.json')
args=parser.parse_args()
refs={p['ref'] for p in json.loads((ROOT/'hardware/rev-a/connectivity.json').read_text())['parts'] if not p['ref'].startswith('#')}
result={}
for fp in children(loads(args.board.read_text(encoding='utf-8')),'footprint'):
    ref=next(p[2] for p in children(fp,'property') if p[1]=='Reference')
    if ref not in refs:continue
    at=first(fp,'at');face=first(fp,'layer')[1]
    if face not in {'F.Cu','B.Cu'}:raise ValueError(f'Invalid face: {ref}')
    result[ref]={'x':round(float(at[1])-100,6),'y':round(122.86-float(at[2]),6),
                 'rotation':round(float(at[3])%360,6) if len(at)>3 else 0,'side':face[0]}
if set(result)!=refs:raise ValueError('Schematic / placement component set differs')
args.output.write_text(json.dumps(dict(sorted(result.items())),indent=2)+'\n',encoding='utf-8',newline='\n')
print(f'Preserved all {len(result)} component positions, rotations and faces in {args.output}')
