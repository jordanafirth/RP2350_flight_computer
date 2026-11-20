"""Export native pad/track geometry for local placement and routing review."""
import json
import math
import argparse
from pathlib import Path
from native_cad import pcbnew,load_board
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--board',type=Path,default=ROOT/'hardware/rev-a/flight-computer.kicad_pcb')
parser.add_argument('--strict-vias',action='store_true')
args=parser.parse_args()
b=load_board(args.board.resolve(),ROOT/'hardware/rev-a/flight-computer.kicad_pro')
def xy(p):return [round(pcbnew.ToMM(p.x),6),round(pcbnew.ToMM(p.y),6)]
def bounds(item):
    box=item.GetBoundingBox()
    return [round(pcbnew.ToMM(v),6) for v in [box.GetX(),box.GetY(),box.GetX()+box.GetWidth(),box.GetY()+box.GetHeight()]]
parts=[];pads=[];tracks=[]
for fp in b.GetFootprints():
    ref=fp.GetReference()
    fp.BuildCourtyardCaches()
    courtyard={}
    for layer in (pcbnew.F_CrtYd,pcbnew.B_CrtYd):
        poly=fp.GetCourtyard(layer)
        if poly.IsEmpty():continue
        box=poly.BBox()
        courtyard[b.GetLayerName(layer)]=[round(pcbnew.ToMM(v),6) for v in [box.GetX(),box.GetY(),box.GetX()+box.GetWidth(),box.GetY()+box.GetHeight()]]
    parts.append({'ref':ref,'position':xy(fp.GetPosition()),'rotation':fp.GetOrientationDegrees(),
        'side':b.GetLayerName(fp.GetLayer()),'footprint':fp.GetFPID().GetUniStringLibId(),'courtyard':courtyard})
    for p in fp.Pads():
        pads.append({'ref':ref,'pad':p.GetNumber(),'net':p.GetNetname(),'position':xy(p.GetPosition()),
            'bounds':bounds(p),'size':xy(p.GetSize()),'rotation':p.GetOrientationDegrees(),
            'layers':[b.GetLayerName(l) for l in p.GetLayerSet().CuStack()],
            'drill':xy(p.GetDrillSize())})
for t in b.GetTracks():
    via=isinstance(t,pcbnew.PCB_VIA)
    row={'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'via':via,
        'layers':[b.GetLayerName(l) for l in t.GetLayerSet().CuStack()],'bounds':bounds(t),
        'width':pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu) if via else t.GetWidth())}
    if via:row.update(position=xy(t.GetPosition()),drill=pcbnew.ToMM(t.GetDrillValue()))
    else:row.update(start=xy(t.GetStart()),end=xy(t.GetEnd()))
    tracks.append(row)
path=ROOT/'.cache/layout-geometry.json'
path.write_text(json.dumps({'parts':parts,'pads':pads,'tracks':tracks},indent=2)+'\n',encoding='utf-8',newline='\n')
vip=[]
for v in tracks:
    if not v['via']:continue
    x,y=v['position']
    for p in pads:
        if len(p['layers'])!=1 or p['layers'][0] not in {'F.Cu','B.Cu'}:continue
        left,top,right,bottom=p['bounds']
        distance=math.hypot(max(left-x,0,x-right),max(top-y,0,y-bottom))
        if distance>=v['drill']/2-1e-6:continue
        vip.append({'via':v['position'],'via_net':v['net'],'ref':p['ref'],'pad':p['pad'],'pad_net':p['net'],
            'test_point':p['ref'].startswith('TP'),'planned_processor_ep':p['ref']=='U4' and p['pad']=='P$1'})
(ROOT/'.cache/via-in-pad-audit.json').write_text(json.dumps({'status':'conservative pad-bounds screening; review exact land shapes',
    'matches':vip},indent=2)+'\n',encoding='utf-8',newline='\n')
print(f'Exported {len(parts)} footprints, {len(pads)} pads and {len(tracks)} track/via items to {path}')
print(f'Via-drill / SMD land screening: {len(vip)} matches; {sum(not p["test_point"] and not p["planned_processor_ep"] for p in vip)} need review beyond the specified processor EP process.')
if args.strict_vias and any(not p['test_point'] and not p['planned_processor_ep'] for p in vip):
    raise SystemExit('Unexpected via drill overlaps a solder land; review before continuing')
