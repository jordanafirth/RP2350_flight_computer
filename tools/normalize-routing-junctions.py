"""Split physical junctions and connect off-centre via contacts explicitly.

Keeps the original routed copper paths. New short spokes lie at existing
same-net contacts. Independent native clearance/connectivity checks follow.
"""
import argparse,copy,json,math,uuid
from collections import defaultdict
from pathlib import Path
from kicad_sexpr import loads,dumps,first,Quoted as Q
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
g=json.loads((ROOT/'.cache/layout-geometry.json').read_text());d=loads(a.source.read_text(encoding='utf-8'))
nodes={first(n,'uuid')[1]:n for n in d if isinstance(n,list) and n[0]=='segment'}
segments=[t for t in g['tracks'] if not t['via'] and t['uuid'] in nodes]
groups=defaultdict(list);vias=defaultdict(list);lands=defaultdict(list)
for t in segments:groups[(t['net'],t['layers'][0])].append(t)
for v in g['tracks']:
    if v['via']:vias[v['net']].append(v)
for pad in g['pads']:
    for layer in pad['layers']:lands[(pad['net'],layer)].append(pad)
cuts={t['uuid']:{0.,1.} for t in segments};spokes=[];spoke_keys={(t['net'],t['layers'][0],tuple(sorted(tuple(round(v,6) for v in p) for p in (t['start'],t['end'])))) for t in segments}
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def sub(a,b):return (a[0]-b[0],a[1]-b[1])
def point(t,f):return tuple(t['start'][k]+f*(t['end'][k]-t['start'][k]) for k in (0,1))
def project(p,t):
    v=sub(t['end'],t['start']);den=v[0]**2+v[1]**2
    f=sum((p[k]-t['start'][k])*v[k] for k in (0,1))/den if den else 0
    return max(0.,min(1.,f))
def cut(t,f):
    length=math.dist(t['start'],t['end'])
    if length and min(f,1-f)*length>.00001:cuts[t['uuid']].add(round(f,12))
def spoke(t,p,z):
    p=tuple(round(x,6) for x in p);z=tuple(round(x,6) for x in z)
    key=(t['net'],t['layers'][0],tuple(sorted((p,z))))
    if math.dist(p,z)<.000001 or key in spoke_keys:return
    spoke_keys.add(key);spokes.append((t,p,z))
for t in segments:
    for v in vias[t['net']]:
        f=project(v['position'],t);q=point(t,f)
        if math.dist(q,v['position'])<=v['width']/2+t['width']/2-.000001:
            cut(t,f);spoke(t,q,v['position'])
            for endpoint in (t['start'],t['end']):
                if math.dist(endpoint,v['position'])<=v['width']/2+t['width']/2-.000001:spoke(t,endpoint,v['position'])
    for pad in lands[(t['net'],t['layers'][0])]:
        f=project(pad['position'],t);q=point(t,f);left,top,right,bottom=pad['bounds'];cx,cy=pad['position']
        rx=(right-left)/2;ry=(bottom-top)/2
        if rx>0 and ry>0 and ((q[0]-cx)/rx)**2+((q[1]-cy)/ry)**2<.98**2:cut(t,f)
for items in groups.values():
    for i,t in enumerate(items):
        r=sub(t['end'],t['start'])
        for z in items[i+1:]:
            s=sub(z['end'],z['start']);den=cross(r,s);delta=sub(z['start'],t['start'])
            if abs(den)>1e-12:
                ft=cross(delta,s)/den;fz=cross(delta,r)/den
                if 0<=ft<=1 and 0<=fz<=1:cut(t,ft);cut(z,fz)
            for source,target in ((t,z),(z,t)):
                for end in (source['start'],source['end']):
                    f=project(end,target);q=point(target,f)
                    if math.dist(end,q)<.001:
                        cut(target,f);spoke(source,end,q)
def number(v):return str(round(v,6))
def make(t,start,end,retain=False,width=None):
    n=copy.deepcopy(nodes[t['uuid']]);first(n,'start')[1:]=[number(v) for v in start];first(n,'end')[1:]=[number(v) for v in end]
    if not retain:first(n,'uuid')[1]=Q(str(uuid.uuid4()))
    if width is not None:first(n,'width')[1]=number(width)
    return n
replacement={};splits=0
for t in segments:
    fs=sorted(cuts[t['uuid']]);result=[]
    for f,z in zip(fs,fs[1:]):
        start,end=point(t,f),point(t,z)
        if math.dist(start,end)<.000001:continue
        result.append(make(t,start,end,retain=not result))
    replacement[t['uuid']]=result;splits+=max(0,len(result)-1)
out=[]
for n in d:
    if isinstance(n,list) and n[0]=='segment':out.extend(replacement.get(first(n,'uuid')[1],[n]))
    else:out.append(n)
out.extend(make(t,start,end,width=.1) for t,start,end in spokes)
a.output.write_text(dumps(out)+'\n',encoding='utf-8',newline='\n')
report={'source':a.source.name,'output':a.output.name,'original_segments':len(segments),'splits':splits,'contact_spokes':len(spokes),'status':'native DRC required'}
(ROOT/'reports/pcb/routing-junction-normalization.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(report))
