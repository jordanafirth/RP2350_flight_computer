"""Screen saved zone fills beneath the USB route; not an impedance solver."""
import argparse
import json
import math
from pathlib import Path
from native_cad import pcbnew, load_board

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--board',type=Path,required=True)
parser.add_argument('--report',type=Path,default=ROOT/'reports/pcb/usb-return-check.json')
args=parser.parse_args()
args.board=args.board.resolve();args.report=args.report.resolve()
b=load_board(args.board,ROOT/'hardware/rev-a/flight-computer.kicad_pro')
reference=pcbnew.In4_Cu if b.GetCopperLayerCount()==6 else pcbnew.In2_Cu
def xy(p):return tuple(pcbnew.ToMM(v) for v in (p.x,p.y))
def vec(x,y):return pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y))
def distance(p,a,z):
    dx,dy=z[0]-a[0],z[1]-a[1]
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.dist(p,(a[0]+t*dx,a[1]+t*dy))
ground=[z.GetFilledPolysList(reference) for z in b.Zones()
        if not z.GetIsRuleArea() and z.GetNetname()=='GND' and z.GetLayer()==reference]
if not ground or not any(p.OutlineCount() for p in ground):
    raise SystemExit('Refill and save L3 GND before this check')
usb={'USB_D+','USB_D-'}
transitions=[xy(t.GetPosition()) for t in b.GetTracks() if isinstance(t,pcbnew.PCB_VIA) and t.GetNetname() in usb]
routes=[t for t in b.GetTracks() if not isinstance(t,pcbnew.PCB_VIA) and t.GetLayer()==pcbnew.B_Cu and t.GetNetname() in usb]
samples=0;near_transition=0;gaps=[]
for t in routes:
    a,z=xy(t.GetStart()),xy(t.GetEnd());count=max(1,math.ceil(math.dist(a,z)/.2))
    for i in range(count+1):
        x,y=(a[k]+(z[k]-a[k])*i/count for k in (0,1))
        if any(math.dist((x,y),v)<.8 for v in transitions):
            near_transition+=1;continue
        samples+=1
        if not any(p.Contains(vec(x,y)) for p in ground):gaps.append({'net':t.GetNetname(),'x':round(x,4),'y':round(y,4)})
foreign=[]
for v in b.GetTracks():
    if not isinstance(v,pcbnew.PCB_VIA) or v.GetNetname() in usb|{'GND'}:continue
    p=xy(v.GetPosition());radius=pcbnew.ToMM(v.GetWidth(pcbnew.F_Cu))/2
    separation=min((distance(p,xy(t.GetStart()),xy(t.GetEnd()))-pcbnew.ToMM(t.GetWidth())/2-radius for t in routes),default=999)
    if separation<.3:foreign.append({'net':v.GetNetname(),'position':p,'copper_edge_distance_mm':round(separation,4)})
result={'status':'pass' if not gaps and not foreign else 'review required','board':args.board.name,
        'reference_layer':b.GetLayerName(reference)+' / GND','trace_center_samples_with_reference':samples-len(gaps),
        'samples_without_reference':gaps,'transition_samples_excluded_within_0p8mm':near_transition,
        'foreign_vias_within_0p3mm_copper_edge':foreign,
        'limits':'Geometric saved-fill screen only. Excludes the local layer-transition regions, which require return-via review. Does not establish impedance, signal integrity or fabrication suitability.'}
args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in result.items() if k not in {'samples_without_reference','limits'}},indent=2))
if gaps or foreign:raise SystemExit(1)
