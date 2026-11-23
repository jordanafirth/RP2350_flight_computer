"""Locate distinct saved-fill ground clusters and their component pads."""
import argparse,json,math
from pathlib import Path
from native_cad import pcbnew,load_board
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--report',type=Path,default=ROOT/'reports/pcb/ground-islands.json');a=p.parse_args()
b=load_board(a.board.resolve(),ROOT/'hardware/rev-a/flight-computer.kicad_pro');nodes=[]
def xy(p):return (pcbnew.ToMM(p.x),pcbnew.ToMM(p.y))
def vec(p):return pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in p))
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname()!='GND':continue
    poly=z.GetFilledPolysList(z.GetLayer())
    for i in range(poly.OutlineCount()):
        chain=poly.Outline(i);pts=[xy(chain.CPoint(j)) for j in range(chain.PointCount())]
        area=abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(pts,pts[1:]+pts[:1])))/2
        nodes.append({'layer':z.GetLayer(),'name':b.GetLayerName(z.GetLayer()),'island':i,'poly':poly,'bounds':[min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)],'area':area,'pads':set(),'through':set()})
parent=list(range(len(nodes)))
def root(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
def join(indices):
    if not indices:return
    r=root(indices[0])
    for i in indices[1:]:parent[root(i)]=r
def hits(points,layers):
    found=[]
    for i,n in enumerate(nodes):
        if n['layer'] not in layers:continue
        left,top,right,bottom=n['bounds']
        if any(left<=p[0]<=right and top<=p[1]<=bottom and n['poly'].Contains(vec(p),n['island']) for p in points):found.append(i)
    return found
for f in b.GetFootprints():
    for pad in f.Pads():
        if pad.GetNetname()!='GND':continue
        x,y=xy(pad.GetPosition());box=pad.GetBoundingBox();sx,sy=xy(box.GetSize());rx=sx/2+.05;ry=sy/2+.05
        points=[(x,y)]+[(x+rx*math.cos(k*math.pi/4),y+ry*math.sin(k*math.pi/4)) for k in range(8)]
        found=hits(points,set(pad.GetLayerSet().CuStack()));join(found);label=f.GetReference()+'/'+pad.GetNumber()
        for i in found:nodes[i]['pads'].add(label)
        if len(pad.GetLayerSet().CuStack())>1:
            for i in found:nodes[i]['through'].add(label)
for t in b.GetTracks():
    if t.GetNetname()!='GND':continue
    if isinstance(t,pcbnew.PCB_VIA):
        x,y=xy(t.GetPosition());r=pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))/2+.05
        points=[(x,y)]+[(x+r*math.cos(k*math.pi/4),y+r*math.sin(k*math.pi/4)) for k in range(8)]
        found=hits(points,{pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu});join(found)
        for i in found:nodes[i]['through'].add('via '+str((round(x,3),round(y,3))))
    else:
        start,end=xy(t.GetStart()),xy(t.GetEnd());count=max(1,math.ceil(math.dist(start,end)/.15));points=[(start[0]+(end[0]-start[0])*k/count,start[1]+(end[1]-start[1])*k/count) for k in range(count+1)]
        join(hits(points,{t.GetLayer()}))
clusters={}
for i,n in enumerate(nodes):
    c=clusters.setdefault(root(i),{'outline_area_mm2':0,'pads':set(),'through_contacts':set(),'islands':[]})
    c['outline_area_mm2']+=n['area'];c['pads']|=n['pads'];c['through_contacts']|=n['through'];c['islands'].append({'layer':n['name'],'island':n['island'],'bounds':n['bounds'],'area_mm2':round(n['area'],4),'pads':sorted(n['pads'])})
result=[]
for c in sorted(clusters.values(),key=lambda c:-c['outline_area_mm2']):
    c['outline_area_mm2']=round(c['outline_area_mm2'],4);c['pads']=sorted(c['pads']);c['through_contacts']=sorted(c['through_contacts']);result.append(c)
a.report.write_text(json.dumps({'status':'saved-fill contact analysis; native DRC remains authoritative','clusters':result},indent=2)+'\n',encoding='utf-8',newline='\n')
for k,c in enumerate(result):
    print('Cluster',k,'area',c['outline_area_mm2'],'pads',','.join(c['pads']))
    if k:
        for n in c['islands']:print(' ',n['layer'],n['island'],[round(v,3) for v in n['bounds']],n['pads'])
