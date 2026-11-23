"""Join saved-fill ground clusters with checked ordinary off-pad vias."""
import argparse,json,math,runpy,sys
from collections import defaultdict
from pathlib import Path
from native_cad import pcbnew,save_board
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();source=a.source.resolve();output=a.output.resolve()
sys.argv=['analyze-ground-islands.py','--board',str(source)]
m=runpy.run_path(str(ROOT/'tools/analyze-ground-islands.py'));b=m['b'];nodes=m['nodes'];root=m['root'];join=m['join'];hits=m['hits']
g=json.loads((ROOT/'.cache/layout-geometry.json').read_text());bins=defaultdict(list)
def index(kind,item,box):
    for x in range(math.floor(box[0]),math.floor(box[2])+1):
        for y in range(math.floor(box[1]),math.floor(box[3])+1):bins[(x,y)].append((kind,item))
for pad in g['pads']:
    box=pad['bounds'];margin=.325
    if max(pad['drill'])>0:
        x,y=pad['position'];r=max(pad['drill'])/2+.325;box=[min(box[0],x-r),min(box[1],y-r),max(box[2],x+r),max(box[3],y+r)]
    index('pad',pad,[box[0]-margin,box[1]-margin,box[2]+margin,box[3]+margin])
for t in g['tracks']:
    if t['net']=='GND':continue
    r=t['width']/2+.325
    if t['via']:x,y=t['position'];box=[x-r,y-r,x+r,y+r]
    else:aa,zz=t['start'],t['end'];box=[min(aa[0],zz[0])-r,min(aa[1],zz[1])-r,max(aa[0],zz[0])+r,max(aa[1],zz[1])+r]
    index('via' if t['via'] else 'track',t,box)
existing=[m['xy'](t.GetPosition()) for t in b.GetTracks() if isinstance(t,pcbnew.PCB_VIA)]
def segdist(p,aa,z):
    dx,dy=z[0]-aa[0],z[1]-aa[1];f=max(0,min(1,((p[0]-aa[0])*dx+(p[1]-aa[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.dist(p,(aa[0]+f*dx,aa[1]+f*dy))
def clear(p):
    x,y=p
    if not (100.6<=x<=150.2 and 100.6<=y<=122.26):return False
    for cx,cy,sx,sy in [(102.54,102.54,-1,-1),(148.26,102.54,1,-1),(102.54,120.32,-1,1),(148.26,120.32,1,1)]:
        if sx*(x-cx)>0 and sy*(y-cy)>0 and math.dist(p,(cx,cy))>2.04:return False
    if any(math.dist(p,q)<.55 for q in existing):return False
    for kind,t in bins[(math.floor(x),math.floor(y))]:
        if kind=='pad':
            left,top,right,bottom=t['bounds'];distance=math.hypot(max(left-x,0,x-right),max(top-y,0,y-bottom))
            drill=max(t['drill'])
            if drill and math.dist(p,t['position'])<drill/2+.325:return False
            if len(t['layers'])==1 and distance<(.20 if t['net']=='GND' else .315):return False
            if len(t['layers'])>1 and t['net']!='GND' and distance<.315:return False
        elif kind=='via':
            if math.dist(p,t['position'])<t['width']/2+.315:return False
        elif segdist(p,t['start'],t['end'])<t['width']/2+.315:return False
    return True
def roots():
    result=defaultdict(list)
    for i in range(len(nodes)):result[root(i)].append(i)
    return result
initial=roots();main=max(initial,key=lambda k:sum(nodes[i]['area'] for i in initial[k]));added=[];unresolved=[]
for target,indices in sorted(initial.items(),key=lambda kv:-sum(nodes[i]['area'] for i in kv[1])):
    if root(target)==root(main):continue
    candidates=set()
    for i in indices:
        left,top,right,bottom=nodes[i]['bounds']
        for xx in range(math.ceil((left-.15)*20),math.floor((right+.15)*20)+1):
            for yy in range(math.ceil((top-.15)*20),math.floor((bottom+.15)*20)+1):candidates.add((xx/20,yy/20))
    best=None
    for p in sorted(candidates):
        if not clear(p):continue
        samples=[p]+[(p[0]+.15*math.cos(k*math.pi/4),p[1]+.15*math.sin(k*math.pi/4)) for k in range(8)]
        touched=hits(samples,{pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu});connected={root(i) for i in touched}
        if root(target) not in connected or len(connected)<2:continue
        score=(root(main) in connected,len(connected))
        if best is None or score>best[0]:best=(score,p,touched)
        if score[0] and score[1]>=2:break
    if best is None:
        labels=sorted(set().union(*(nodes[i]['pads'] for i in indices)));unresolved.append(labels);print('No ordinary off-pad site:',labels,flush=True);continue
    _,p,touched=best;v=pcbnew.PCB_VIA(b);v.SetPosition(m['vec'](p));v.SetWidth(pcbnew.FromMM(.4));v.SetDrill(pcbnew.FromMM(.2));v.SetViaType(pcbnew.VIATYPE_THROUGH);v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);v.SetNet(b.FindNet('GND'));v.SetLocked(True);b.Add(v);existing.append(p);join(touched)
    added.append({'x':p[0],'y':p[1],'diameter_mm':.4,'drill_mm':.2});print('Ground cluster stitch:',p,flush=True)
save_board(b,output)
(ROOT/'reports/pcb/ground-cluster-stitching.json').write_text(json.dumps({'status':'native DRC required','vias_added':added,'clusters_without_an_off_pad_site':unresolved},indent=2)+'\n',encoding='utf-8',newline='\n')
print('Added',len(added),'ordinary off-pad ground vias')
