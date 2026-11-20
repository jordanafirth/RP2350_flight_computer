"""Prepare a separate candidate with short, explicitly routed BNO085 loops.

The working PCB is untouched. Retain GND vias, replace provisional signal
routing, and preserve these local B.Cu connections during subsequent routing.
"""
import json
import math
from pathlib import Path
from kicad_sexpr import loads,dumps,first
from native_cad import pcbnew,load_board,save_board

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/rev-a'
CACHE=ROOT/'.cache/routing'
path=CACHE/'candidate-sensor-placement.kicad_pcb'
data=loads((OUT/'flight-computer.kicad_pcb').read_text(encoding='utf-8'))
data[:]=[n for n in data if not (isinstance(n,list) and n[0] in {'segment','via','arc'}
    and not (n[0]=='via' and first(n,'net')[1]=='GND'))]
path.write_text(dumps(data)+'\n',encoding='utf-8',newline='\n')
board=load_board(path,OUT/'flight-computer.kicad_pro')
fps={f.GetReference():f for f in board.GetFootprints()}
# Native KiCad mm coordinates, rotation and face. Only passive parts move.
placement={
    # Restore the common baseline before later offset-placement experiments.
    'U5':(124,111.86,0),
    'Y2':(123,115.3,180),
    'C31':(123.25,108.3,90),'C32':(119.65,113.4,180),
    'C33':(121.75,117.95,270),'C34':(124.25,117.95,270),
    'C35':(119.65,111.9,180),
    'R41':(119.55,110.25,0),'R42':(124.8,108.3,270),
    'R43':(128.5,112.6,180),'R44':(127.5,108.5,270),'R45':(128.3,111,180),
    'R32':(120.25,118.06,90),'R33':(125.75,118.16,90),'R34':(127.3,117.86,90),
    'C38':(117,114.56,90),'TP4':(136.5,104.5,0),'TP5':(138.5,104.5,0),
}
for ref,(x,y,angle) in placement.items():
    fp=fps[ref]
    if fp.GetLayer()!=pcbnew.B_Cu:raise ValueError('Unexpected face: '+ref)
    fp.SetOrientationDegrees(angle)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))

def pad(ref,num):return next(p for p in fps[ref].Pads() if p.GetNumber()==num)
def xy(p):return (pcbnew.ToMM(p.x),pcbnew.ToMM(p.y))
routes=[]
def wire(net,a,b,waypoints=(),width=.15):
    pa,pb=pad(*a),pad(*b)
    if pa.GetNetname()!=net or pb.GetNetname()!=net:raise ValueError(f'Wrong endpoint for {net}: {a}, {b}')
    points=[xy(pa.GetPosition()),*waypoints,xy(pb.GetPosition())]
    length=0
    for start,end in zip(points,points[1:]):
        if start==end:continue
        t=pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(start[0]),pcbnew.FromMM(start[1])))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(end[0]),pcbnew.FromMM(end[1])))
        t.SetWidth(pcbnew.FromMM(width));t.SetLayer(pcbnew.B_Cu)
        t.SetNet(board.FindNet(net));t.SetLocked(True);board.Add(t)
        length+=((start[0]-end[0])**2+(start[1]-end[1])**2)**.5
    routes.append({'net':net,'from':a,'to':b,'points':points,'width_mm':width,'length_mm':round(length,3)})

wire('BNO_XIN',('U5','27'),('Y2','1'),[(122.75,114.3)])
wire('BNO_XOUT',('U5','26'),('Y2','2'),[(123.25,114.3)])
wire('BNO_XIN',('Y2','1'),('C33','1'))
wire('BNO_XOUT',('Y2','2'),('C34','1'))
wire('BNO_CAP',('U5','9'),('C31','1'))
wire('BNO_BOOT_N',('U5','4'),('R41','2'),[(121.1,111.61),(121.1,110.975)])
wire('BNO_RESET_N',('U5','11'),('R42','2'),[(124.25,109.675)])
wire('BNO_CS_N',('U5','18'),('R43','2'),[(127.185,112.11)])
wire('BNO_AUX_SCL',('U5','15'),('R44','2'),[(126.25,109.575),(126.5,109.325)])
wire('BNO_AUX_SDA',('U5','16'),('R45','2'),[(127.365,111.11)])
wire('+3V3',('U5','3'),('C35','1'),[(120.635,112.11)])
wire('+3V3',('U5','28'),('C32','1'),[(122.25,114.05),(121.075,114.05)])

def distance_to_segment(x,y,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    f=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(x-a[0]-f*dx,y-a[1]-f*dy)
# A free-standing via can be re-netted by KiCad when a moved pad covers it.
# Remove obsolete ground stitches before that can turn one into an unintended
# supply via-in-pad; retain the deliberate MCU exposed-pad vias when clear.
foreign_boxes=[]
for fp in board.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname()=='GND':continue
        b=p.GetBoundingBox()
        foreign_boxes.append(tuple(pcbnew.ToMM(v) for v in [b.GetX(),b.GetY(),b.GetX()+b.GetWidth(),b.GetY()+b.GetHeight()]))
foreign_tracks=[t for t in board.GetTracks() if not isinstance(t,pcbnew.PCB_VIA) and t.GetNetname()!='GND']
remove=set();removed_vias=[]
for v in board.GetTracks():
    if not isinstance(v,pcbnew.PCB_VIA):continue
    x,y=xy(v.GetPosition());radius=pcbnew.ToMM(v.GetWidth(pcbnew.F_Cu))/2
    blocked=any(math.hypot(max(a-x,0,x-c),max(b-y,0,y-d))<radius+.11 for a,b,c,d in foreign_boxes)
    blocked|=any(distance_to_segment(x,y,xy(t.GetStart()),xy(t.GetEnd()))<radius+pcbnew.ToMM(t.GetWidth())/2+.11 for t in foreign_tracks)
    blocked|=121.15<x<124.85 and 114.3<y<116.3
    if blocked:remove.add(v.m_Uuid.AsString());removed_vias.append({'x':x,'y':y})
save_board(board,path)
saved=loads(path.read_text(encoding='utf-8'))
saved[:]=[n for n in saved if not (isinstance(n,list) and n[0]=='via' and first(n,'uuid')[1] in remove)]
path.write_text(dumps(saved)+'\n',encoding='utf-8',newline='\n')
report={'status':'local routing candidate; independent KiCad DRC required',
    'placements':{r:{'x':x-100,'y':round(122.86-y,6),'rotation':a,'side':'B'} for r,(x,y,a) in placement.items()},
    'routes':routes,'obsolete_ground_vias_removed':removed_vias,
    'limits':'Preserves sensor pin mapping and passive values. Does not establish oscillator startup or assembly fit on physical boards.'}
(ROOT/'reports/pcb/sensor-local-routing.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(f'Prepared {len(placement)} support-part/test-pad moves, {len(routes)} local connections, removed {len(remove)} obsolete ground vias in {path}')
