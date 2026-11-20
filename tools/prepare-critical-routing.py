"""Route USB explicitly on a separate, sensor-optimized layout candidate.

No desktop control and no working-board replacement. Copper dimensions are
provisional until the fabricator confirms the stackup and impedance geometry.
"""
import json
import math
import argparse
from pathlib import Path
from native_cad import pcbnew, load_board, save_board
from kicad_sexpr import loads, dumps, first

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware/rev-a'
CACHE = ROOT / '.cache/routing'
parser=argparse.ArgumentParser()
parser.add_argument('--escape-flash',action='store_true')
args=parser.parse_args()
variant='escape' if args.escape_flash else 'critical'
TARGET = CACHE / f'candidate-{variant}-placement.kicad_pcb'
data = loads((CACHE / 'candidate-sensor-placement.kicad_pcb').read_text(encoding='utf-8'))
# Replace the moved auxiliary pull-up's previous local connection.
data[:] = [n for n in data if not (isinstance(n, list) and n[0] in {'segment', 'arc'}
                                 and first(n, 'net')[1] in ({'BNO_AUX_SDA','BNO_CS_N'} if args.escape_flash else {'BNO_AUX_SDA'}))]
TARGET.write_text(dumps(data) + '\n', encoding='utf-8', newline='\n')
b = load_board(TARGET, OUT / 'flight-computer.kicad_pro')
fps = {f.GetReference(): f for f in b.GetFootprints()}
placements = {
    'U3': (110.35, 114.0, 90), 'C20': (111, 111.3, 90),
    'R9': (128.4, 111.75, 180), 'R10': (128.4, 110.35, 180),
    'C17': (130.95, 111.584, 0), 'TP3': (140.5, 104.5, 0),
    'R45': (128.25, 106.0, 180),
    'C7': (123.9775,107.65,270), 'C21': (128.75,117.2,0),
    'R14': (128.75,119.1,90), 'R1': (126.1447,119.2643,0),
    'R35': (131.1,117.96,90),
}
if args.escape_flash:
    placements.update({'R9':(129.5,111.75,180),'R10':(129.5,110.35,180),
                       'C17':(132.05,111.584,0),'R43':(127.8,114.8,180)})
def point(p): return tuple(pcbnew.ToMM(v) for v in (p.x, p.y))
def vec(p): return pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in p))
def pad(ref, number): return next(p for p in fps[ref].Pads() if p.GetNumber() == number)
def loc(ref, number): return point(pad(ref, number).GetPosition())
for ref, (x, y, angle) in placements.items():
    fps[ref].SetOrientationDegrees(angle)
    fps[ref].SetPosition(vec((x, y)))
routes = []
def wire(net, points, layer=pcbnew.F_Cu, width=.13):
    for a, z in zip(points, points[1:]):
        if a == z: continue
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(vec(a)); t.SetEnd(vec(z)); t.SetWidth(pcbnew.FromMM(width))
        t.SetLayer(layer); t.SetNet(b.FindNet(net)); t.SetLocked(True); b.Add(t)
    routes.append({'net': net, 'layer': b.GetLayerName(layer), 'width_mm': width,
                   'points': points, 'length_mm': round(sum(math.dist(a,z) for a,z in zip(points,points[1:])), 3)})
def via(net, xy):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(vec(xy)); v.SetWidth(pcbnew.FromMM(.4)); v.SetDrill(pcbnew.FromMM(.2))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(b.FindNet(net)); v.SetLocked(True); b.Add(v)

if args.escape_flash:
    wire('BNO_AUX_SDA',[loc('U5','16'),(125.5,111.11)],pcbnew.B_Cu,.15)
    via('BNO_AUX_SDA',(125.5,111.11));via('BNO_AUX_SDA',(126.5,108.8))
    wire('BNO_AUX_SDA',[(125.5,111.11),(126.5,110.11),(126.5,108.8)],pcbnew.In2_Cu,.15)
    wire('BNO_AUX_SDA',[(126.5,108.8),(126.5,106),loc('R45','2')],pcbnew.B_Cu,.15)
    wire('BNO_CS_N',[loc('U5','18'),(126.98,112.11),(126.98,114.305),loc('R43','2')],pcbnew.B_Cu,.15)
else:
    wire('BNO_AUX_SDA', [loc('U5','16'), (126.98,111.11), (127.69,110.4),
         (128.65,110.4), (128.65,107.225), loc('R45','2')], pcbnew.B_Cu, .15)
# Connector's duplicate contacts need explicit jumps; an ordinary pair route
# cannot connect the interleaved D-/D+/D-/D+ land ordering without a crossing.
contacts = [('B7','USB_D-',110.68), ('A6','USB_D+',111.18),
            ('A7','USB_D-',111.68), ('B6','USB_D+',112.18)]
for number, net, y in contacts:
    assert pad('JUSB1',number).GetNetname() == net
    wire(net, [loc('JUSB1',number), (108.44,y)])
    via(net,(108.44,y))
wire('USB_D-', [(108.44,110.68),(108.04,110.68),(107.84,110.88),
     (107.84,111.48),(108.04,111.68),(108.44,111.68)], pcbnew.B_Cu)
wire('USB_D+', [(108.44,111.18),(108.9,111.18),(109.1,111.38),
     (109.1,111.98),(108.9,112.18),(108.44,112.18)], pcbnew.B_Cu)
wire('USB_D-', [(108.44,110.68),(110.5,110.68)], pcbnew.B_Cu)
wire('USB_D+', [(108.44,111.18),(109.76,111.18),(110,110.94),(110.5,110.94)], pcbnew.B_Cu)

center = [(110.5,110.81),(112.8,110.81),(113.1,110.51),(113.1,103.3),
          (113.4,103),(129.7,103),(130,103.3),(130,110.825),(129.7,111.125),(129.55,111.125)]
def offset_polyline(points, offset):
    shifted = []
    for a,z in zip(points,points[1:]):
        dx,dy = z[0]-a[0],z[1]-a[1]; length=math.hypot(dx,dy)
        ox,oy=-dy/length*offset,dx/length*offset
        shifted.append(((a[0]+ox,a[1]+oy),(z[0]+ox,z[1]+oy)))
    result=[shifted[0][0]]
    for (a,z),(c,d) in zip(shifted,shifted[1:]):
        ux,uy=z[0]-a[0],z[1]-a[1]; vx,vy=d[0]-c[0],d[1]-c[1]
        t=((c[0]-a[0])*vy-(c[1]-a[1])*vx)/(ux*vy-uy*vx)
        result.append((a[0]+t*ux,a[1]+t*uy))
    return result+[shifted[-1][1]]
for net,offset,ref,y in [('USB_D+',.13,'R10',110.35),('USB_D-',-.13,'R9',111.75)]:
    path=offset_polyline(center,offset)
    wire(net,path,pcbnew.B_Cu)
    if args.escape_flash:
        transition=(129.4,109.75) if net=='USB_D+' else (129.6,112.35)
        wire(net,[path[-1],transition],pcbnew.B_Cu);via(net,transition)
        points=([transition,(130.4,109.75),(130.4,110.35),loc(ref,'1')] if net=='USB_D+'
                else [transition,(130.008,112.35),loc(ref,'1')])
        wire(net,points)
    else:
        wire(net,[path[-1],(129.7,y)],pcbnew.B_Cu)
        via(net,(129.7,y)); wire(net,[(129.7,y),loc(ref,'1')])
plus_x,minus_x=(128.2,128.6) if args.escape_flash else (127.25,127.65)
wire('D+', [loc('U4','52'),(plus_x,113.1),(plus_x,110.35),loc('R10','2')])
wire('D-', [loc('U4','51'),(minus_x,113.5),(minus_x,111.75),loc('R9','2')])
if args.escape_flash:
    for number,x in [('59',127.75),('58',127.15),('57',127.75),('56',127.15),('55',127.75),('60',128.4)]:
        p=pad('U4',number);net=p.GetNetname();start=point(p.GetPosition())
        end=(x,start[1])
        wire(net,[start,end],width=.1);via(net,end)
    # Staggered top-row escapes keep through vias outside all solder lands.
    for number,x in [('7',123.35),('8',122.8),('9',122.25),('10',121.7),
                     ('12',121.15),('13',120.6),('15',119.5)]:
        p=pad('U4',number);start=point(p.GetPosition());end=(x,108.3)
        knee=(start[0],108.3+abs(start[0]-x))
        points=[start,(123.5775,108.9),(123.35,108.6725),end] if number=='7' else [start,knee,end]
        if number=='8':points=[start,(123.1775,108.9),(122.8,108.5225),end]
        wire(p.GetNetname(),points,width=.1);via(p.GetNetname(),end)
    for number,end,knee_y in [('5',(124.7775,108.3),108.7),('4',(125.35,108.3),108.8725)]:
        p=pad('U4',number);start=point(p.GetPosition())
        wire(p.GetNetname(),[start,(start[0],knee_y),end],width=.1);via(p.GetNetname(),end)
    wire('+3V3',[loc('U4','11'),(121.9775,110),(121.4775,110.5),(121.2,110.5)],width=.15)
    via('+3V3',(121.2,110.5))
for xy in [(108.44,109.8),(130.5,110.9)]: via('GND',xy)
if args.escape_flash:
    via('GND',(131,109.7))

# Explicit short buck-converter loop and separate feedback connection.
wire('LX',[loc('U4','48'),(127.8,114.7),(128.2765,115.1765)],width=.2)
wire('LX',[(128.2765,115.1765),(129.988,115.1765),loc('L1','P$2')],width=.4)
wire('+3V3',[loc('U4','49'),(127.8,114.3)],width=.2)
wire('+3V3',[(127.8,114.3),loc('C13','1')],width=.3)
wire('GND',[loc('U4','47'),(127.4,115.1),(128.1,115.8)],width=.2)
wire('GND',[(128.1,115.8),loc('C13','2'),loc('C8','2')],width=.35)
wire('GND',[(128.1,115.8),(127.9,115.8)],width=.2)
wire('GND',[loc('C8','2'),(129.9085,117.4)],width=.35)
for xy in [(127.9,115.8),(129.9085,117.4)]:via('GND',xy)
wire('VCORE',[loc('L1','P$1'),loc('C8','1')],width=.5)
feedback=([loc('U4','50'),(127.7,113.9),(127.835,113.765),(129.1,113.765),(129.965,112.9),(131.988,112.9),loc('L1','P$1')]
          if args.escape_flash else [loc('U4','50'),(128,113.9),(129,112.9),(131.988,112.9),loc('L1','P$1')])
wire('VCORE',feedback,width=.15)
wire('VREG_AVDD',[loc('U4','46'),(127.3,115.5),(127.3,116.258),loc('C21','1')],width=.15)
wire('VREG_AVDD',[loc('C21','1'),(128.242,118.084),loc('R14','2')],width=.15)
wire('GND',[loc('C21','2'),(129.9085,117.4)],width=.2)

output=(132.3,116.65);top=(124.025,108.7) if args.escape_flash else (122.4,108.158)
left=(118.075,113.3);bottom=(123.25,116.85)
for xy in [output,top,left,bottom]:via('VCORE',xy)
wire('VCORE',[loc('C8','1'),output],width=.4)
wire('VCORE',[loc('U4','6'),loc('C7','2')],width=.15)
wire('VCORE',[loc('C7','2'),top],width=.2)
wire('VCORE',[loc('U4','23'),(119.1925,112.7),(119.1925,113.05),(118.9425,113.3),left,loc('C18','2')],width=.13)
wire('VCORE',[loc('U4','39'),(123.5775,116.7),(123.4275,116.85),bottom,loc('C6','2')],width=.15)
trunk_x=128.9 if args.escape_flash else 128.4
if args.escape_flash:
    wire('VCORE',[output,(130.6,114.95),(trunk_x,114.95),(trunk_x,106.4),(124.025,106.4),top],pcbnew.In2_Cu,.3)
    wire('VCORE',[(124.025,106.4),(117.2,106.4),(117.2,112.425),left],pcbnew.In2_Cu,.3)
else:
    wire('VCORE',[output,(130.6,114.95),(trunk_x,114.95),(trunk_x,108.158),top],pcbnew.In2_Cu,.3)
    wire('VCORE',[top,(118.075,112.483),left],pcbnew.In2_Cu,.3)
wire('VCORE',[output,(129.35,119.6),(123.25,119.6)],pcbnew.In2_Cu,.3)
wire('VCORE',[(123.25,119.6),bottom],pcbnew.In2_Cu,.15)
for ref,end in [('C7',(124.65,105.7) if args.escape_flash else (123.9775,106.35)),('C18',(118.95,115.2)),('C6',(124.95,119.05))]:
    wire('GND',[loc(ref,'1'),end],width=.15);via('GND',end)
# Reserve the adjacent inner layer as a return reference for the B.Cu pair.
# Pours and vias remain allowed; audit foreign vias before release.
for index,(x1,y1,x2,y2) in enumerate([(108.2,110.2,113.8,111.6),(112.4,102.3,113.8,111.5),
    (112.4,102.3,130.7,103.7),(129.3,102.3,130.7,112.4),(107.1,110,109.9,112.9)]):
    z=pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetLayer(pcbnew.In2_Cu)
    z.SetZoneName(f'USB return reference {index+1}')
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(False)
    z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    outline=z.Outline(); outline.NewOutline()
    for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]: outline.Append(pcbnew.FromMM(x),pcbnew.FromMM(y))
    b.Add(z)
# Moving a land over a previously free ground stitch must not silently re-net
# that via. Remove obsolete free stitches before KiCad's refill step.
removed=[]
for v in b.GetTracks():
    if not isinstance(v,pcbnew.PCB_VIA) or v.IsLocked() or v.GetNetname()!='GND':continue
    x,y=point(v.GetPosition()); radius=pcbnew.ToMM(v.GetWidth(pcbnew.F_Cu))/2
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname()=='GND':continue
            box=p.GetBoundingBox();a,c=point(box.GetPosition());w,h=point(box.GetSize())
            if math.hypot(max(a-x,0,x-a-w),max(c-y,0,y-c-h))<radius+.11:
                removed.append(v.m_Uuid.AsString());break
        else:continue
        break
save_board(b,TARGET)
saved=loads(TARGET.read_text(encoding='utf-8'))
saved[:]=[n for n in saved if not (isinstance(n,list) and n[0]=='via' and first(n,'uuid')[1] in removed)]
TARGET.write_text(dumps(saved)+'\n',encoding='utf-8',newline='\n')
report={'status':'independent DRC and impedance confirmation required',
        'placements_native_mm':placements,'routes':routes,'obsolete_ground_vias_removed':len(removed),
        'usb_geometry':{'width_mm':.13,'gap_mm':.13,'target_ohms':90,'impedance_verified':False,
                        'provisional_stackup':'JLC04161H-3313; fabricator confirmation required'}}
(ROOT/f'reports/pcb/{variant}-local-routing.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(f'Prepared {len(routes)} fixed local routes in {TARGET}')
