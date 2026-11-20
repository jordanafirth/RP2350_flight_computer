"""Find nearby top-side USB resistor sites using actual KiCad courtyards.

Writes a placement study only. The working PCB is never modified by this tool.
Routing and return-path review are separate from physical courtyard clearance.
"""
import json
import math
from pathlib import Path
from native_cad import pcbnew, load_board

ROOT=Path(__file__).resolve().parents[1]
board=load_board(ROOT/'hardware/rev-a/flight-computer.kicad_pcb')
fps={f.GetReference():f for f in board.GetFootprints()}
obstacles=[]
pad_boxes=[]
for ref,fp in fps.items():
    if ref in {'R9','R10'}:continue
    for pad in fp.Pads():
        if pcbnew.F_Cu not in pad.GetLayerSet().CuStack():continue
        b=pad.GetBoundingBox()
        pad_boxes.append(tuple(pcbnew.ToMM(v) for v in [b.GetX(),b.GetY(),b.GetX()+b.GetWidth(),b.GetY()+b.GetHeight()]))
    fp.BuildCourtyardCaches()
    p=fp.GetCourtyard(pcbnew.F_CrtYd)
    if not p.IsEmpty():obstacles.append((ref,pcbnew.SHAPE_POLY_SET(p)))

def overlap(a,b):
    if not a.BBox().Intersects(b.BBox()):return False
    p=pcbnew.SHAPE_POLY_SET(a)
    p.BooleanIntersection(b)
    return p.Area()>1

sites={}
for ref,target in [('R9',(126.5775,113.5)),('R10',(126.5775,113.1))]:
    fp=fps[ref]
    if fp.GetLayer()==pcbnew.B_Cu:fp.Flip(fp.GetPosition(),pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(180)
    options=[]
    for xi in range(510,525):
        for yi in range(437,462):
            x,y=xi/4,yi/4
            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))
            fp.BuildCourtyardCaches()
            poly=pcbnew.SHAPE_POLY_SET(fp.GetCourtyard(pcbnew.F_CrtYd))
            if any(overlap(poly,o) for _,o in obstacles):continue
            blocked=False
            for pad in fp.Pads():
                b=pad.GetBoundingBox()
                a,bottom,c,d=(pcbnew.ToMM(v) for v in [b.GetX(),b.GetY(),b.GetX()+b.GetWidth(),b.GetY()+b.GetHeight()])
                if any(a-.15<right and c+.15>left and bottom-.15<upper and d+.15>lower for left,lower,right,upper in pad_boxes):
                    blocked=True;break
            if blocked:continue
            pin=next(p for p in fp.Pads() if p.GetNumber()=='2').GetPosition()
            px,py=pcbnew.ToMM(pin.x),pcbnew.ToMM(pin.y)
            score=math.hypot(px-target[0],py-target[1])
            options.append((score,x,y,poly))
    sites[ref]=sorted(options,key=lambda s:s[0])[:100]

combinations=[]
for a in sites['R9']:
    for b in sites['R10']:
        if a[2]<=b[2] or overlap(a[3],b[3]):continue
        score=a[0]+b[0]+abs(a[1]-b[1])+.25*abs(a[2]-b[2]-.8)
        combinations.append((score,a,b))
if not combinations:raise SystemExit('No clear pair found in the search area')
score,a,b=min(combinations,key=lambda s:s[0])
result={'status':'courtyard placement study; copper routing still requires review',
    'resistors':{ref:{'x':site[1]-100,'y':122.86-site[2],'rotation':180,'side':'F',
        'pad2_distance_to_mcu_mm':round(site[0],3)} for ref,site in [('R9',a),('R10',b)]}}
path=ROOT/'.cache/usb-placement-options.json'
path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result,indent=2))
