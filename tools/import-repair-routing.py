"""Apply proposed grid-search connections to a separate native scratch board."""
import argparse
import json
from pathlib import Path
from native_cad import pcbnew,load_board,save_board
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--routes',type=Path,required=True)
args=parser.parse_args()
source=args.source.resolve();output=args.output.resolve()
if source==output:raise ValueError('Use a separate scratch board for repair proposals')
data=json.loads(args.routes.read_text(encoding='utf-8'))
b=load_board(source,ROOT/'hardware/rev-a/flight-computer.kicad_pro')
def vec(p):return pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in p))
count=0;vias=0
for route in data['routes']:
    net=b.FindNet(route['net'])
    if not net:raise ValueError('Unknown route net '+route['net'])
    for chunk in route['chunks']:
        layer=b.GetLayerID(chunk['layer'])
        if layer not in (pcbnew.F_Cu,pcbnew.In2_Cu,pcbnew.B_Cu):raise ValueError('Unsupported routing layer')
        for a,z in zip(chunk['points'],chunk['points'][1:]):
            if a==z:continue
            t=pcbnew.PCB_TRACK(b);t.SetStart(vec(a));t.SetEnd(vec(z))
            t.SetLayer(layer);t.SetWidth(pcbnew.FromMM(route['width_mm']));t.SetNet(net)
            t.SetLocked(True);b.Add(t);count+=1
    for p in route['vias']:
        v=pcbnew.PCB_VIA(b);v.SetPosition(vec(p));v.SetWidth(pcbnew.FromMM(.4));v.SetDrill(pcbnew.FromMM(.2))
        v.SetViaType(pcbnew.VIATYPE_THROUGH);v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
        v.SetNet(net);v.SetLocked(True);b.Add(v);vias+=1
save_board(b,output)
print(f'Applied {count} proposed segments and {vias} vias to {output}; independent checks required')
