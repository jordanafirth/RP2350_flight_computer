"""Move the IMU circuit off the processor escape ring in a scratch candidate."""
import json
import math
from pathlib import Path
from native_cad import pcbnew,load_board,save_board
from kicad_sexpr import loads,dumps,first
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hardware/rev-a';CACHE=ROOT/'.cache/routing'
path=CACHE/'candidate-offset-placement.kicad_pcb'
data=loads((CACHE/'candidate-escape-placement.kicad_pcb').read_text(encoding='utf-8'))
data[:]=[n for n in data if not (isinstance(n,list) and n[0] in {'segment','via','arc'} and first(n,'net')[1] in {'BNO_AUX_SDA','BNO_AUX_SCL'})]
path.write_text(dumps(data)+'\n',encoding='utf-8',newline='\n')
b=load_board(path,OUT/'flight-computer.kicad_pro');fps={f.GetReference():f for f in b.GetFootprints()}
def xy(p):return tuple(pcbnew.ToMM(v) for v in (p.x,p.y))
def vec(p):return pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in p))
def pad(ref,num):return next(p for p in fps[ref].Pads() if p.GetNumber()==num)
shifted=['U5','Y2','C31','C32','C33','C34','C35','R41','R42','R43','R44']
for ref in shifted:
    x,y=xy(fps[ref].GetPosition());fps[ref].SetPosition(vec((x-5,y)))
for t in b.GetTracks():
    if isinstance(t,pcbnew.PCB_VIA):continue
    if t.GetLayer()==pcbnew.B_Cu and (t.GetNetname().startswith('BNO_') or t.GetNetname()=='+3V3'):
        for getter,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
            x,y=xy(getter());setter(vec((x-5,y)))
old={p.GetNumber():(p.GetNetname(),xy(p.GetPosition())) for p in fps['R41'].Pads()}
fps['R41'].SetPosition(vec((114.85,110.25)))
for number,(net,where) in old.items():
    dest=pad('R41',number).GetPosition()
    for t in b.GetTracks():
        if isinstance(t,pcbnew.PCB_VIA) or t.GetNetname()!=net:continue
        for getter,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
            if math.dist(xy(getter()),where)<.00001:setter(dest)
extras=[('R45',(124.3,110.5),90),('R44',(126.5,107),270),('C38',(116.2,104.3),0),('C4',(115.4,106.6),0),('R4',(119.2,105.6),180)]
extras += [(f'R{31+i}',(121.3+1.7*i,118.1),90) for i in range(6)]
for ref,position,angle in extras:
    fps[ref].SetOrientationDegrees(angle);fps[ref].SetPosition(vec(position))
def wire(net,points,layer=pcbnew.B_Cu,width=.15):
    for a,z in zip(points,points[1:]):
        t=pcbnew.PCB_TRACK(b);t.SetStart(vec(a));t.SetEnd(vec(z));t.SetLayer(layer)
        t.SetWidth(pcbnew.FromMM(width));t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
wire('BNO_AUX_SDA',[xy(pad('U5','16').GetPosition()),(121.98,111.11),(122.69,110.4),(123.575,110.4),xy(pad('R45','2').GetPosition())])
wire('BNO_AUX_SCL',[xy(pad('U5','15').GetPosition()),(121.25,108.7),(123.4,108.7),(123.8,109.1),(124.5,109.1),(124.9,108.7),(126.5,108.7),xy(pad('R44','2').GetPosition())])
def joint(net,old,new):
    for t in b.GetTracks():
        if t.GetNetname()!=net:continue
        if isinstance(t,pcbnew.PCB_VIA):
            if math.dist(xy(t.GetPosition()),old)<.002:t.SetPosition(vec(new))
        else:
            for getter,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
                if math.dist(xy(getter()),old)<.002:setter(vec(new))
for net,old,new in [('+3V3',(121.2,110.5),(120.5,111.1)),
    ('VCORE',(118.075,113.3),(118.65,114.08)),('GND',(118.95,115.2),(117.6,115.2)),
    ('VCORE',(123.25,116.85),(122.15,116.85)),('VCORE',(123.25,119.6),(122.15,119.6)),
    ('GND',(124.95,119.05),(123.85,117)),('GND',(129.9085,117.4),(130.65,117.4))]:joint(net,old,new)
cap_ground=xy(pad('C6','1').GetPosition())
for t in b.GetTracks():
    if isinstance(t,pcbnew.PCB_VIA) or t.GetNetname()!='GND':continue
    if any(math.dist(xy(getter()),cap_ground)<.00001 for getter in (t.GetStart,t.GetEnd)) and any(math.dist(xy(getter()),(123.85,117))<.00001 for getter in (t.GetStart,t.GetEnd)):
        t.SetStart(vec(cap_ground));t.SetEnd(vec((124.1,cap_ground[1])))
wire('GND',[(124.1,cap_ground[1]),(124.1,117.25),(123.85,117)],pcbnew.F_Cu)
foreign=[];solder_lands=[]
for fp in b.GetFootprints():
    for p in fp.Pads():
        box=p.GetBoundingBox();x,y=xy(box.GetPosition());w,h=xy(box.GetSize())
        if p.GetNetname()!='GND':foreign.append((x,y,x+w,y+h))
        if len(list(p.GetLayerSet().CuStack()))==1 and not fp.GetReference().startswith('TP') and not (fp.GetReference()=='U4' and p.GetNumber()=='P$1'):
            solder_lands.append((x,y,x+w,y+h))
def distance(p,a,z):
    dx,dy=z[0]-a[0],z[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.dist(p,(a[0]+t*dx,a[1]+t*dy))
signal=[t for t in b.GetTracks() if not isinstance(t,pcbnew.PCB_VIA) and t.GetNetname()!='GND']
remove=set()
for v in b.GetTracks():
    if not isinstance(v,pcbnew.PCB_VIA) or v.GetNetname()!='GND' or v.IsLocked():continue
    x,y=xy(v.GetPosition());r=pcbnew.ToMM(v.GetWidth(pcbnew.F_Cu))/2
    if any(math.hypot(max(a-x,0,x-c),max(bb-y,0,y-d))<r+.11 for a,bb,c,d in foreign) or any(distance((x,y),xy(t.GetStart()),xy(t.GetEnd()))<r+.11+pcbnew.ToMM(t.GetWidth())/2 for t in signal) or any(math.hypot(max(a-x,0,x-c),max(bb-y,0,y-d))<.15 for a,bb,c,d in solder_lands):
        remove.add(v.m_Uuid.AsString())
save_board(b,path)
data=loads(path.read_text(encoding='utf-8'))
data[:]=[n for n in data if not (isinstance(n,list) and n[0]=='via' and first(n,'uuid')[1] in remove)]
path.write_text(dumps(data)+'\n',encoding='utf-8',newline='\n')
report={'status':'independent physical DRC required','imu_shift_native_mm':[-5,0],
        'shifted_parts':shifted,'obsolete_ground_vias_removed':len(remove),
        'placements':{r:{'position':xy(fps[r].GetPosition()),'rotation':fps[r].GetOrientationDegrees(),'side':'B'} for r in sorted(set(shifted+[p[0] for p in extras]))},
        'limits':'Reuses exact parts and local sensor topology. Board outline and connector locations are unchanged. Physical prototype and assembly review remain required.'}
(ROOT/'reports/pcb/offset-placement.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Prepared 5-mm IMU shift and local support-part placement in',path)
