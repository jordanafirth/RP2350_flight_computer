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
parser.add_argument('--max-nodes',type=int,default=650000)
parser.add_argument('--deduplicate-only',action='store_true')
parser.add_argument('--fanout',action='store_true',help='Prepare short pad escapes to the inner signal layer before global routing.')
parser.add_argument('--net',action='append',help='Limit proposals to the selected net; repeat for multiple nets.')
parser.add_argument('--layers',help='Comma-separated permitted signal layers for this local repair.')
parser.add_argument('--width-mm',type=float,help='Explicit reviewed width for a targeted routing repair.')
parser.add_argument('--route-ground',action='store_true',help='Route ground using explicitly grouped saved-fill geometry.')
parser.add_argument('--ground-fanout',action='store_true',help='Connect ground solder lands to local through vias and the L2 ground plane.')
parser.add_argument('--fanout-ref',action='append',help='Limit reserved escapes to these component references.')
parser.add_argument('--local-l2',action='store_true',help='Permit short L2 bridges, preferring front ground reference and excluding fast front traces.')
parser.add_argument('--l2-budget-mm',type=float,default=4.)
parser.add_argument('--inner-crossings',action='store_true',help='Allow L2 crossings beneath SD/QSPI fanout; retain USB, crystal and switch-node reference exclusions. Prototype SI review required.')
parser.add_argument('--fanout-pad',action='append',help='Limit ground fanout to ref/pad pairs.')
args=parser.parse_args()
g=json.loads(args.geometry.read_text(encoding='utf-8'))
drc=json.loads(args.drc.read_text(encoding='utf-8'))
layers=args.layers.split(',') if args.layers else g.get('routing_layers',['F.Cu','In2.Cu','B.Cu']);layer_count=len(layers);step=.05
x0=y0=100.;nx=1017;ny=459;size=nx*ny
pads=g['pads'];tracks=g['tracks'];lookup={t['uuid']:t for t in tracks}
components={}
for item in pads+tracks:
    if item.get('component'):components.setdefault(item['component'],[]).append(item)
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
l2_reference=None
l2_region=None
if args.local_l2:
    data=json.loads((ROOT/'.cache/l2-reference-mask.json').read_text(encoding='utf-8'))
    l2_reference=np.zeros((ny,nx),dtype=bool)
    l2_region=(X[None,:]>=100.6)&(X[None,:]<=150.2)&(Y[:,None]>=100.6)&(Y[:,None]<=122.2)
    for n in data['allowed']:
        xx=int(round((data['x0']+n%data['nx']*data['step']-x0)/step));yy=int(round((data['y0']+n//data['nx']*data['step']-y0)/step))
        if 0<=xx<nx and 0<=yy<ny:l2_reference[yy,xx]=True
keepouts=[(108.2,110.2,113.8,111.6),(112.4,102.3,113.8,111.5),
          (112.4,102.3,130.7,103.7),(129.3,102.3,130.7,112.4),(107.1,110,109.9,112.9)]
if g.get('copper_layer_count',4)==6:keepouts=[]
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
    clearance=.2 if not args.fanout and net in {'VBAT','VBUS','VSYS','VBAT_SERVO'} else .1
    inflation=width/2+clearance+.0125
    blocked=np.zeros((layer_count,ny,nx),dtype=bool);via_block=np.zeros((ny,nx),dtype=bool)
    for m in blocked:edge(m,width/2)
    edge(via_block,.2)
    for area in g.get('track_keepouts',[]):
        for points in area['polygons']:
            mask=np.zeros((ny,nx),dtype=bool)
            for a,z in zip(points,points[1:]+points[:1]):
                if abs(z[1]-a[1])>1e-12:
                    mask^=((Y[:,None]>a[1])!=(Y[:,None]>z[1]))&(X[None,:]<(z[0]-a[0])*(Y[:,None]-a[1])/(z[1]-a[1])+a[0])
            for a,z in zip(points,points[1:]+points[:1]):segment(mask,a,z,width/2+.0125)
            for i,layer in enumerate(layers):
                if layer in area['layers']:blocked[i]|=mask
    if args.local_l2 and 'In1.Cu' in layers:
        allowed=l2_reference.copy()
        for p in original_vias.get(net,[]):disk(allowed,p,.6)
        # Short bridges can also reference adjacent coplanar ground. Their
        # actual saved ground coverage and transition returns are checked
        # after refill; prefer an additional front ground reference here.
        blocked[layers.index('In1.Cu')]|=~l2_region
        fast={'D+','D-','USB_D+','USB_D-','BASE_N_5','BASE_N_6','BASE_N_7','SD_CLK','SD_MOSI','SD_MISO','SD_CS','LX','VREG_AVDD'}
        for t in tracks:
            if not t['via'] and 'F.Cu' in t['layers'] and (t['net'] in fast or t['net'].startswith('QSPI_')):
                if args.inner_crossings and (t['net'].startswith('QSPI_') or t['net'] in {'SD_CLK','SD_MOSI','SD_MISO','SD_CS'}):continue
                shadow=np.zeros((ny,nx),dtype=bool);exempt=np.zeros((ny,nx),dtype=bool)
                margin=.4 if t['net'] in {'D+','D-','USB_D+','USB_D-','BASE_N_5','BASE_N_6','BASE_N_7','LX','VREG_AVDD'} else .3
                segment(shadow,t['start'],t['end'],t['width']/2+margin)
                for p in original_vias.get(net,[]):disk(exempt,p,.6 if t['net']==net else .35)
                blocked[layers.index('In1.Cu')]|=shadow&~exempt
    if 'In2.Cu' in layers and net!='GND':
        for box in keepouts:rect(blocked[layers.index('In2.Cu')],box,width/2+.0125)
    for p in pads:
        if max(p['drill'])>0 and not p['net']:
            x,y=p['position'];r=max(p['drill'])/2
            hole=[x-r,y-r,x+r,y+r]
            for mask in blocked:rect(mask,hole,width/2+.2+.0125)
            rect(via_block,hole,.2+.2+.0125)
        if p['net']!=net:
            for i,l in enumerate(layers):
                if l in p['layers']:
                    pad_inflation=width/2+max(clearance,.2 if max(p['drill'])>0 and not p['net'] else clearance)+.0125
                    rect(blocked[i],p['bounds'],pad_inflation)
        # New drills must stay away from every solder land, including own-net
        # pads. Existing through connections are handled separately below.
        rect(via_block,p['bounds'],(.2 if args.ground_fanout else .15) if p['net']==net else .2+clearance+.0125)
    for t in tracks:
        if t['net']==net:
            if t['via']:disk(via_block,t['position'],.425)
            continue
        radius=t['width']/2
        for i,l in enumerate(layers):
            if l not in t['layers']:continue
            if t['via']:disk(blocked[i],t['position'],radius+inflation)
            else:segment(blocked[i],t['start'],t['end'],radius+inflation)
        via_clearance=max(clearance,.31) if t['net'] in {'USB_D+','USB_D-','D+','D-'} else clearance
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
def endpoints(item,blocked,expand=True):
    if expand and not args.fanout and item.get('component'):
        result={}
        for member in components[item['component']]:result.update(endpoints(member,blocked,False))
        return result
    result={}
    if item.get('fanout'):
        left,top,right,bottom=item['bounds'];layer=layers.index('In1.Cu' if args.ground_fanout else 'In2.Cu')
        for x in range(max(0,math.ceil((left-x0)/step)),min(nx,math.floor((right-x0)/step)+1)):
            for y in range(max(0,math.ceil((top-y0)/step)),min(ny,math.floor((bottom-y0)/step)+1)):
                if not blocked[layer,y,x]:result[layer*size+y*nx+x]=point(x,y)
        return result
    if 'start' in item:
        a,z=item['start'],item['end'];count=max(1,math.ceil(math.dist(a,z)/step))
        points=[(a[0]+(z[0]-a[0])*i/count,a[1]+(z[1]-a[1])*i/count) for i in range(count+1)]
    else:
        a=item['position'];points=[a]
        if 'pad' in item:
            left,top,right,bottom=item['bounds']
            for xx in np.arange(left+.04,right,.1):
                for yy in np.arange(top+.04,bottom,.1):
                    # A bounding-box corner may lie outside a circular,
                    # oval or rounded solder land. Use an inscribed ellipse
                    # so every proposed endpoint actually touches pad copper.
                    if ((xx-a[0])/((right-left)/2))**2+((yy-a[1])/((bottom-top)/2))**2<=.85**2:
                        points.append((float(xx),float(yy)))
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
    dist=np.full(layer_count*size,np.inf);parent=np.full(layer_count*size,-1,dtype=np.int32);closed=np.zeros(layer_count*size,dtype=bool)
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
            nn=l*size+yy*nx+xx;nc=cost+length*((1.5 if l2_reference[yy,xx] else 2) if args.local_l2 and layers[l]=='In1.Cu' else 1)
            if not closed[nn] and nc<dist[nn]:
                dist[nn]=nc;parent[nn]=n;heapq.heappush(heap,(nc+float(heuristic(xx,yy,l))*1.12,nc,nn))
        if not vblocked[y,x]:
            for ll in range(layer_count):
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
connections=drc['unconnected_items']
if args.inner_crossings:
    priority={'SD_MOSI':0,'QSPI_IO3':1,'SWDIO':2,'BMP_INT':3,'A0':4,'GPIO8':5,'SERVO2':6}
    connections=sorted(connections,key=lambda c:min((rank for net,rank in priority.items() if '['+net+']' in c['items'][0]['description']),default=50))
if args.ground_fanout:
    args.fanout=True
    if 'In1.Cu' not in layers:raise ValueError('Ground fanout requires the L2 ground plane in --layers')
if args.net:
    connections=[c for c in connections if any('['+net+']' in c['items'][0]['description'] for net in args.net)]
if args.fanout:
    # Reserve the difficult remaining terminals before routing neighboring nets.
    selected={}
    for connection in connections:
        for item in connection['items']:
            if re.search(r'\bpad\s',item['description'],re.I):
                p=item_geometry(item)
                if len(p['layers'])==1 and not p['ref'].startswith('TP') and p['net'] not in {'GND','BASE_N_4'}:
                    selected[(p['ref'],p['pad'])]=item
    local={'GND','VCORE','LX','VREG_AVDD','D+','D-','BASE_N_5','BASE_N_6','BASE_N_7'}
    for p in pads:
        if p['ref']=='U4' and p['net'] not in local and not p['net'].startswith('unconnected-'):
            selected[(p['ref'],p['pad'])]={'uuid':'','description':f"Pad {p['pad']} [{p['net']}] of U4",'pos':dict(zip(('x','y'),p['position']))}
        if (p['ref']=='U5' and p['net'] in {'SDA','SCL','BNO_INT_N','BNO_RESET_N'}) or (p['ref']=='U1' and p['net'].startswith('QSPI_')):
            selected[(p['ref'],p['pad'])]={'uuid':'','description':f"Pad {p['pad']} [{p['net']}] of {p['ref']}",'pos':dict(zip(('x','y'),p['position']))}
    pending=[]
    for _,item in sorted(selected.items()):
        p=item_geometry(item)
        if args.fanout_ref and p['ref'] not in args.fanout_ref:continue
        if p['net'] in local:continue
        members=components.get(p.get('component'),[p])
        if any(m.get('via') or ('pad' in m and len(m['layers'])>1) for m in members):continue
        pending.append({'items':[item,{'fanout':True,'description':'Inner-layer via escape'}]})
    connections=pending
if args.ground_fanout:
    connections=[{'items':[{'uuid':p['uuid'],'description':f"Pad {p['pad']} [GND] of {p['ref']}",'pos':dict(zip(('x','y'),p['position']))},{'fanout':True,'description':'L2 ground connection'}]} for p in pads if p['net']=='GND' and (not args.fanout_pad or p['ref']+'/'+p['pad'] in args.fanout_pad) and len(p['layers'])==1 and not (p['ref']=='U4' and p['pad']=='P$1')]
for index,connection in enumerate(connections[:args.limit]):
    aa,zz=connection['items']
    if '[GND]' in aa['description'] and not (args.ground_fanout or args.route_ground):
        failed.append({'net':'GND','reason':'ground handled separately'});continue
    a=item_geometry(aa);net=a['net']
    if zz.get('fanout'):
        x,y=a['position']
        z={'fanout':True,'net':net,'bounds':[x-2,y-2,x+2,y+2]}
    else:z=item_geometry(zz)
    if not args.fanout and a.get('component') and a['component']==z.get('component'):
        continue
    if net!=z['net']:raise ValueError('Unconnected endpoint net mismatch')
    if net=='GND' and not (args.ground_fanout or args.route_ground):failed.append({'net':net,'reason':'ground handled separately'});continue
    width=.4 if net in {'VBAT','VBUS','VSYS','VBAT_SERVO'} else (.15 if net=='+3V3' else .1)
    if args.fanout:width=.15 if net in {'VBAT','VBUS','VSYS','VBAT_SERVO','+3V3'} else .1
    if args.width_mm is not None:width=args.width_mm
    blocked,via_block,reusable=obstacles(net,width)
    found,stats=search(a,z,blocked,via_block,reusable,max_nodes=args.max_nodes)
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
    l2_length=sum(math.dist(a,z) for c in chunks if c['layer']=='In1.Cu' for a,z in zip(c['points'],c['points'][1:]))
    if args.local_l2 and l2_length>args.l2_budget_mm:
        failed.append({'net':net,'reason':'L2 bridge budget','l2_length_mm':l2_length});continue
    route={'net':net,'width_mm':width,'chunks':chunks,'vias':newvias,**stats};routes.append(route)
    added=[]
    for chunk in chunks:
        for p,q in zip(chunk['points'],chunk['points'][1:]):
            added.append({'net':net,'via':False,'layers':[chunk['layer']],'width':width,'start':p,'end':q})
    for p in newvias:added.append({'net':net,'via':True,'position':p,'width':.4,'drill':.2,'layers':layers+['In1.Cu']+(['In4.Cu'] if g.get('copper_layer_count')==6 else [])})
    tracks.extend(added)
    if a.get('component'):
        ca=a['component'];cz=z.get('component')
        joined=components[ca]+(components[cz] if cz and cz!=ca else [])+added
        for member in joined:member['component']=ca
        components[ca]=joined
        if cz:components[cz]=joined
    print(f'{index+1}: {net}: proposed {len(chunks)} layer runs / {len(newvias)} new vias; {stats}',flush=True)
result={'status':'route proposals; native DRC required','source_report':args.drc.name,'routes':routes,'failed':failed,
        'grid_mm':step,'elapsed_seconds':round(time.time()-began,2)}
result=merge_redundant_vias(result)
args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(f'Proposed {len(routes)} connections; {len(failed)} unresolved; saved {args.output}',flush=True)
