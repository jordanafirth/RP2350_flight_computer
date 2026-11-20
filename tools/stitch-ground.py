"""Stitch filled ground islands using conservative copper containment tests.

Run after KiCad DRC --refill-zones --save-board. Every proposed 0.4/0.2-mm
through via must fit the continuous L2 GND reference and clear actual foreign
copper on every layer. Processor exposed-pad vias require filling/capping.
Independent KiCad DRC must follow. This is not a substitute for return-path,
regulator-loop, thermal-pad or assembler review.
"""
import json
import math
from pathlib import Path
from native_cad import pcbnew,load_board,save_board

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'hardware/rev-a/flight-computer.kicad_pcb'
board=load_board(path)
layers=[pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu]
fills={}
for zone in board.Zones():
    if zone.GetNetname()=='GND' and zone.GetLayer() in layers:
        fills[zone.GetLayer()]=zone.GetFilledPolysList(zone.GetLayer())
if set(fills)!=set(layers) or any(p.OutlineCount()==0 for p in fills.values()):
    raise SystemExit('Refill and save all four GND zones before stitching')

def point(x,y):return pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y))
foreign_pads=[]
foreign_tracks=[]
foreign_vias=[]
for fp in board.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname()=='GND':continue
        b=p.GetBoundingBox()
        foreign_pads.append(tuple(pcbnew.ToMM(v) for v in [b.GetX(),b.GetY(),b.GetX()+b.GetWidth(),b.GetY()+b.GetHeight()]))
for t in board.GetTracks():
    if t.GetNetname()=='GND':continue
    if isinstance(t,pcbnew.PCB_VIA):
        p=t.GetPosition();foreign_vias.append((pcbnew.ToMM(p.x),pcbnew.ToMM(p.y),pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))/2))
    else:
        a,b=t.GetStart(),t.GetEnd()
        foreign_tracks.append((pcbnew.ToMM(a.x),pcbnew.ToMM(a.y),pcbnew.ToMM(b.x),pcbnew.ToMM(b.y),pcbnew.ToMM(t.GetWidth())/2))

def segment_distance(x,y,a,b,c,d):
    dx,dy=c-a,d-b
    fraction=max(0,min(1,((x-a)*dx+(y-b)*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(x-a-fraction*dx,y-b-fraction*dy)

def clear_copper(x,y):
    # 12 boundary samples plus the center, with a 0.025-mm radial margin.
    offsets=[(0,0)]+[(.225*math.cos(t*math.pi/6),.225*math.sin(t*math.pi/6)) for t in range(12)]
    if not all(fills[pcbnew.In1_Cu].Contains(point(x+dx,y+dy)) for dx,dy in offsets):return False
    # Other layers can contain empty space where a new ground via will enable
    # the next fill. Check actual foreign copper rather than requiring an
    # already connected ground pour at that location on every layer.
    if any(math.hypot(max(a-x,0,x-c),max(b-y,0,y-d))<.325 for a,b,c,d in foreign_pads):return False
    if any(math.hypot(x-a,y-b)<r+.325 for a,b,r in foreign_vias):return False
    if any(segment_distance(x,y,a,b,c,d)<r+.325 for a,b,c,d,r in foreign_tracks):return False
    return True

pad_boxes=[]
ground_pads=[]
ground_through=[]
for fp in board.GetFootprints():
    for pad in fp.Pads():
        box=pad.GetBoundingBox()
        pad_boxes.append(tuple(pcbnew.ToMM(v) for v in [box.GetX(),box.GetY(),box.GetX()+box.GetWidth(),box.GetY()+box.GetHeight()]))
        if pad.GetNetname()=='GND':
            p=pad.GetPosition();ground_pads.append((pcbnew.ToMM(p.x),pcbnew.ToMM(p.y)))
            if pcbnew.In1_Cu in pad.GetLayerSet().CuStack():ground_through.append(ground_pads[-1])
existing=[]
for track in board.GetTracks():
    if isinstance(track,pcbnew.PCB_VIA):
        p=track.GetPosition();existing.append((pcbnew.ToMM(p.x),pcbnew.ToMM(p.y)))
        if track.GetNetname()=='GND':ground_through.append(existing[-1])

outer=[pcbnew.F_Cu,pcbnew.B_Cu]
uncovered={(layer,i) for layer in outer for i in range(fills[layer].OutlineCount())}
for x,y in ground_through:
    for layer,i in list(uncovered):
        if any(fills[layer].Contains(point(x+.25*math.cos(t*math.pi/4),y+.25*math.sin(t*math.pi/4)),i) for t in range(8)):
            uncovered.discard((layer,i))
options=[]
for xi in range(403,601):
    for yi in range(403,489):
        x,y=xi/4,yi/4
        if any(a-.25<=x<=c+.25 and b-.25<=y<=d+.25 for a,b,c,d in pad_boxes):continue
        if any(math.hypot(x-a,y-b)<.6 for a,b in existing):continue
        coverage={(layer,i) for layer,i in uncovered if fills[layer].Contains(point(x,y),i)}
        if not coverage or not clear_copper(x,y):continue
        distance=min(math.hypot(x-a,y-b) for a,b in ground_pads)
        options.append((x,y,coverage,distance))

added=[]
while options:
    useful=[o for o in options if o[2]&uncovered]
    if not useful:break
    x,y,coverage,_=min(useful,key=lambda o:(-len(o[2]&uncovered),o[3]))
    via=pcbnew.PCB_VIA(board)
    via.SetPosition(point(x,y))
    via.SetWidth(pcbnew.FromMM(.4))
    via.SetDrill(pcbnew.FromMM(.2))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
    via.SetNet(board.FindNet('GND'))
    board.Add(via)
    added.append({'x':x,'y':y,'diameter_mm':.4,'drill_mm':.2})
    uncovered-=coverage
    options=[o for o in options if math.hypot(o[0]-x,o[1]-y)>=.6]

ep_vias=[]
processor=next(fp for fp in board.GetFootprints() if fp.GetReference()=='U4')
ep=next(p for p in processor.Pads() if p.GetNumber()=='P$1').GetPosition()
ex,ey=pcbnew.ToMM(ep.x),pcbnew.ToMM(ep.y)
for track in board.GetTracks():
    if not isinstance(track,pcbnew.PCB_VIA) or track.GetNetname()!='GND':continue
    pos=track.GetPosition();x,y=pcbnew.ToMM(pos.x),pcbnew.ToMM(pos.y)
    if abs(x-ex)<1.6 and abs(y-ey)<1.6:
        ep_vias.append({'x':x,'y':y,'diameter_mm':pcbnew.ToMM(track.GetWidth(pcbnew.F_Cu)),
            'drill_mm':pcbnew.ToMM(track.GetDrillValue()),'process':'filled and copper capped; assembler review required'})
# These sites lie in the cross between the four inherited paste windows.
# Check the underside BNO pads and every other layer before adding each via.
for dx,dy in [(0,0),(.8,0),(-.8,0),(0,-.8),(0,.8)]:
    x,y=ex+dx,ey+dy
    if len(ep_vias)>=3:break
    if any(math.hypot(x-a,y-b)<.6 for a,b in existing):continue
    if not clear_copper(x,y):continue
    via=pcbnew.PCB_VIA(board);via.SetPosition(point(x,y));via.SetWidth(pcbnew.FromMM(.4));via.SetDrill(pcbnew.FromMM(.2))
    via.SetViaType(pcbnew.VIATYPE_THROUGH);via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);via.SetNet(board.FindNet('GND'))
    board.Add(via);ep_vias.append({'x':x,'y':y,'diameter_mm':.4,'drill_mm':.2,'process':'filled and copper capped; assembler review required'})
save_board(board,path)
report={'status':'candidate stitches; independent DRC required','vias_added':added,
    'outer_fill_islands_without_a_new_stitch':[{'layer':board.GetLayerName(l),'island':i} for l,i in sorted(uncovered)],
    'processor_exposed_pad_vias':ep_vias,
    'limits':'Exposed-pad vias require filling and copper capping in the fabrication quote. Uncovered islands may already connect through PTH pads or may need manual routing. Independent DRC and assembler stencil/process review remain required.'}
(ROOT/'reports/pcb/ground-stitching.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(f'Added {len(added)} ground stitches and {len(ep_vias)} filled/capped exposed-pad vias; {len(uncovered)} outer fill islands need connectivity review.')
