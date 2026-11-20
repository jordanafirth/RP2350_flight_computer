"""Conservative grid-search completion of a checked partial routing candidate.

Consumes native geometry and raw KiCad unconnected items; emits route proposals
only. Independent native DRC, via-in-pad and return-reference checks must follow.
Requires NumPy in the separate numerical runtime, not in KiCad's interpreter.
"""
import argparse
import heapq
import json
import math
import re
import time
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--geometry',type=Path,default=ROOT/'.cache/layout-geometry.json')
parser.add_argument('--drc',type=Path,required=True)
parser.add_argument('--output',type=Path,default=ROOT/'.cache/routing/repair-routes.json')
parser.add_argument('--limit',type=int,default=100)
parser.add_argument('--deduplicate-only',action='store_true')
args=parser.parse_args()
g=json.loads(args.geometry.read_text(encoding='utf-8'))
drc=json.loads(args.drc.read_text(encoding='utf-8'))
layers=['F.Cu','In2.Cu','B.Cu'];step=.05
x0=y0=100.;nx=1017;ny=459;size=nx*ny
pads=g['pads'];tracks=g['tracks'];lookup={t['uuid']:t for t in tracks}
original_vias={}
for t in tracks:
    if t['via']:original_vias.setdefault(t['net'],[]).append(t['position'])
def merge_redundant_vias(result):
    known={net:list(points) for net,points in original_vias.items()};merged=[]
    for route in result['routes']:
        points=known.setdefault(route['net'],[]);keep=[]
        for p in route['vias']:
            nearest=min(points,key=lambda q:math.dist(p,q)) if points else None
            if nearest is not None and math.dist(p,nearest)<=.125:
                merged.append({'net':route['net'],'proposed':p,'reused':nearest})
            else:keep.append(p);points.append(p)
        route['vias']=keep
    result['via_connections_reusing_existing_annuli']=merged
    return result
if args.deduplicate_only:
    result=merge_redundant_vias(json.loads(args.output.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Reused {len(result["via_connections_reusing_existing_annuli"])} existing same-net via annuli; native DRC required')
    raise SystemExit(0)
X=x0+np.arange(nx)*step;Y=y0+np.arange(ny)*step
keepouts=[(108.2,110.2,113.8,111.6),(112.4,102.3,113.8,111.5),
          (112.4,102.3,130.7,103.7),(129.3,102.3,130.7,112.4),(107.1,110,109.9,112.9)]
def grid(p):return (int(round((p[0]-x0)/step)),int(round((p[1]-y0)/step)))
def point(x,y):return (round(x0+x*step,6),round(y0+y*step,6))
def rect(mask,box,inflation):
    a,b,c,d=box
    ix0=max(0,int(math.ceil((a-inflation-x0)/step)));ix1=min(nx,int(math.floor((c+inflation-x0)/step))+1)
    iy0=max(0,int(math.ceil((b-inflation-y0)/step)));iy1=min(ny,int(math.floor((d+inflation-y0)/step))+1)
    if ix1>ix0 and iy1>iy0:mask[iy0:iy1,ix0:ix1]=True
def disk(mask,p,radius):
    a,b=p;ix0=max(0,int((a-radius-x0)/step));ix1=min(nx,int((a+radius-x0)/step)+2)
    iy0=max(0,int((b-radius-y0)/step));iy1=min(ny,int((b+radius-y0)/step)+2)
    if ix1>ix0 and iy1>iy0:mask[iy0:iy1,ix0:ix1]|=(X[None,ix0:ix1]-a)**2+(Y[iy0:iy1,None]-b)**2<=radius*radius
def segment(mask,a,z,radius):
    dx,dy=z[0]-a[0],z[1]-a[1]
    ix0=max(0,int((min(a[0],z[0])-radius-x0)/step));ix1=min(nx,int((max(a[0],z[0])+radius-x0)/step)+2)
    iy0=max(0,int((min(a[1],z[1])-radius-y0)/step));iy1=min(ny,int((max(a[1],z[1])+radius-y0)/step)+2)
    if ix1<=ix0 or iy1<=iy0:return
    xx=X[None,ix0:ix1];yy=Y[iy0:iy1,None]
    f=np.clip(((xx-a[0])*dx+(yy-a[1])*dy)/(dx*dx+dy*dy),0,1) if dx or dy else 0
    mask[iy0:iy1,ix0:ix1]|=(xx-a[0]-f*dx)**2+(yy-a[1]-f*dy)**2<=radius*radius
def edge(mask,radius):
    clearance=.25+radius+.025
    mask|=(X[None,:]<100+clearance)|(X[None,:]>150.8-clearance)|(Y[:,None]<100+clearance)|(Y[:,None]>122.86-clearance)
    for cx,cy,sx,sy in [(102.54,102.54,-1,-1),(148.26,102.54,1,-1),(102.54,120.32,-1,1),(148.26,120.32,1,1)]:
        corner=(sx*(X[None,:]-cx)>0)&(sy*(Y[:,None]-cy)>0)
        mask|=corner&((X[None,:]-cx)**2+(Y[:,None]-cy)**2>(2.54-clearance)**2)
def obstacles(net,width):
    clearance=.2 if net in {'VBAT','VBUS','VSYS','VBAT_SERVO'} else .1
    inflation=width/2+clearance+.0125
    blocked=np.zeros((3,ny,nx),dtype=bool);via_block=np.zeros((ny,nx),dtype=bool)
    for m in blocked:edge(m,width/2)
    edge(via_block,.2)
    for box in keepouts:rect(blocked[1],box,width/2+.0125)
    for p in pads:
        if p['net']!=net:
            for i,l in enumerate(layers):
                if l in p['layers']:rect(blocked[i],p['bounds'],inflation)
        # New drills must stay away from every solder land, including own-net
        # pads. Existing through connections are handled separately below.
        rect(via_block,p['bounds'],.15 if p['net']==net else .2+clearance+.0125)
    for t in tracks:
        if t['net']==net:
            if t['via']:disk(via_block,t['position'],.425)
            continue
        radius=t['width']/2
        for i,l in enumerate(layers):
            if l not in t['layers']:continue
            if t['via']:disk(blocked[i],t['position'],radius+inflation)
            else:segment(blocked[i],t['start'],t['end'],radius+inflation)
        via_clearance=max(clearance,.31) if t['net'] in {'USB_D+','USB_D-'} else clearance
        if t['via']:disk(via_block,t['position'],radius+.2+via_clearance+.0125)
        else:segment(via_block,t['start'],t['end'],radius+.2+via_clearance+.0125)
    reusable=set()
    for t in tracks:
        if t['net']==net and t['via']:
            cx,cy=grid(t['position'])
            for dx in range(-2,3):
                for dy in range(-2,3):
                    if math.dist(point(cx+dx,cy+dy),t['position'])<=.125:reusable.add((cx+dx,cy+dy))
    for p in pads:
        if p['net']==net and max(p['drill'])>0:reusable.add(grid(p['position']))
    for x,y in reusable:
        if 0<=x<nx and 0<=y<ny:via_block[y,x]=False
    return blocked,via_block,reusable
def item_geometry(item):
    if item['uuid'] in lookup:return lookup[item['uuid']]
    desc=item['description'];number=re.search(r'\bpad\s+(\S+)',desc,re.I);ref=re.search(r'\bof\s+(\S+)',desc)
    if not number or not ref:raise ValueError('Unsupported endpoint: '+desc)
    options=[p for p in pads if p['ref']==ref[1] and p['pad']==number[1]]
    return min(options,key=lambda p:math.dist(p['position'],(item['pos']['x'],item['pos']['y'])))
def endpoints(item,blocked):
    result={}
    if 'start' in item:
        a,z=item['start'],item['end'];count=max(1,math.ceil(math.dist(a,z)/step))
        points=[(a[0]+(z[0]-a[0])*i/count,a[1]+(z[1]-a[1])*i/count) for i in range(count+1)]
    else:
        a=item['position'];points=[a]
        if 'pad' in item:
            left,top,right,bottom=item['bounds']
            for xx in np.arange(left+.04,right,.1):
                for yy in np.arange(top+.04,bottom,.1):points.append((float(xx),float(yy)))
    for p in points:
        x,y=grid(p)
        if not (0<=x<nx and 0<=y<ny):continue
        for i,l in enumerate(layers):
            if l in item['layers'] and not blocked[i,y,x]:result[i*size+y*nx+x]=p
    return result
def search(start,goal,blocked,vblocked,reusable,max_nodes=650000):
    starts=endpoints(start,blocked);goals=endpoints(goal,blocked)
    if not starts or not goals:return None,{'reason':'endpoint access','start_cells':len(starts),'goal_cells':len(goals)}
    target=np.array([(n%size%nx,n%size//nx,n//size) for n in goals])
    minx,miny=map(int,target[:,:2].min(axis=0));maxx,maxy=map(int,target[:,:2].max(axis=0))
    goal_layers=set(int(z) for z in target[:,2]);via_cost=24.
    def heuristic(x,y,l):
        dx=max(minx-x,0,x-maxx);dy=max(miny-y,0,y-maxy)
        return max(dx,dy)+.41421356237*min(dx,dy)+(0 if l in goal_layers else via_cost)
    dist=np.full(3*size,np.inf);parent=np.full(3*size,-1,dtype=np.int32);closed=np.zeros(3*size,dtype=bool)
    heap=[]
    for n in starts:
        l=n//size;y=n%size//nx;x=n%nx
        dist[n]=0;heapq.heappush(heap,(float(heuristic(x,y,l))*1.12,0.,n))
    visited=0
    while heap and visited<max_nodes:
        _,cost,n=heapq.heappop(heap)
        if closed[n]:continue
        closed[n]=True;visited+=1
        if n in goals:
            path=[n]
            while parent[path[-1]]!=-1:path.append(int(parent[path[-1]]))
            path.reverse()
            return (path,starts[path[0]],goals[n]),{'expanded':visited}
        l=n//size;y=n%size//nx;x=n%nx
        for dx,dy,length in [(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.41421356),(1,-1,1.41421356),(-1,1,1.41421356),(-1,-1,1.41421356)]:
            xx,yy=x+dx,y+dy
            if not (0<=xx<nx and 0<=yy<ny) or blocked[l,yy,xx]:continue
            if dx and dy and (blocked[l,y,xx] or blocked[l,yy,x]):continue
            nn=l*size+yy*nx+xx;nc=cost+length
            if not closed[nn] and nc<dist[nn]:
                dist[nn]=nc;parent[nn]=n;heapq.heappush(heap,(nc+float(heuristic(xx,yy,l))*1.12,nc,nn))
        if not vblocked[y,x]:
            for ll in range(3):
                if ll==l or blocked[ll,y,x]:continue
                nn=ll*size+y*nx+x;nc=cost+(1. if (x,y) in reusable else via_cost)
                if not closed[nn] and nc<dist[nn]:
                    dist[nn]=nc;parent[nn]=n;heapq.heappush(heap,(nc+float(heuristic(x,y,ll))*1.12,nc,nn))
    return None,{'reason':'search limit' if visited>=max_nodes else 'no path','expanded':visited}
def simplify(points):
    out=[]
    for p in points:
        if out and math.dist(out[-1],p)<1e-7:continue
        while len(out)>1:
            a,z=out[-2:];cross=(z[0]-a[0])*(p[1]-z[1])-(z[1]-a[1])*(p[0]-z[0])
            dot=(z[0]-a[0])*(p[0]-z[0])+(z[1]-a[1])*(p[1]-z[1])
            if abs(cross)>1e-8 or dot<0:break
            out.pop()
        out.append(p)
    return out
routes=[];failed=[];began=time.time()
for index,connection in enumerate(drc['unconnected_items'][:args.limit]):
    aa,zz=connection['items'];a,z=item_geometry(aa),item_geometry(zz);net=a['net']
    if net!=z['net']:raise ValueError('Unconnected endpoint net mismatch')
    if net=='GND':failed.append({'net':net,'reason':'ground handled separately'});continue
    width=.4 if net in {'VBAT','VBUS','VSYS','VBAT_SERVO'} else (.15 if net=='+3V3' else .1)
    blocked,via_block,reusable=obstacles(net,width)
    found,stats=search(a,z,blocked,via_block,reusable)
    if not found:
        failed.append({'net':net,'from':aa['description'],'to':zz['description'],**stats})
        print(f'{index+1}: {net}: not completed {stats}',flush=True);continue
    path,start,end=found;chunks=[];newvias=[];current=[];old_layer=None
    for n in path:
        l=n//size;y=n%size//nx;x=n%nx;p=point(x,y)
        if old_layer is None:current=[start,p]
        elif l!=old_layer:
            chunks.append({'layer':layers[old_layer],'points':simplify(current)})
            if (x,y) not in reusable:newvias.append(p);reusable.add((x,y))
            current=[p]
        else:current.append(p)
        old_layer=l
    current.append(end);chunks.append({'layer':layers[old_layer],'points':simplify(current)})
    route={'net':net,'width_mm':width,'chunks':chunks,'vias':newvias,**stats};routes.append(route)
    for chunk in chunks:
        for p,q in zip(chunk['points'],chunk['points'][1:]):
            tracks.append({'net':net,'via':False,'layers':[chunk['layer']],'width':width,'start':p,'end':q})
    for p in newvias:tracks.append({'net':net,'via':True,'position':p,'width':.4,'drill':.2,'layers':['F.Cu','In1.Cu','In2.Cu','B.Cu']})
    print(f'{index+1}: {net}: proposed {len(chunks)} layer runs / {len(newvias)} new vias; {stats}',flush=True)
result={'status':'route proposals; native DRC required','source_report':args.drc.name,'routes':routes,'failed':failed,
        'grid_mm':step,'elapsed_seconds':round(time.time()-began,2)}
result=merge_redundant_vias(result)
args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(f'Proposed {len(routes)} connections; {len(failed)} unresolved; saved {args.output}',flush=True)
