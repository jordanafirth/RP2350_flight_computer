"""Native KiCad DSN/SES interchange for the engineering routing candidate.

Run with KiCad's bundled Python. The autorouter is a separate local process;
this script does not upload CAD or run any vendor service.
"""
import argparse
import json
from pathlib import Path
from native_cad import pcbnew,load_board,save_board
from kicad_sexpr import loads,dumps,first

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/rev-a'
TARGET=OUT/'flight-computer.kicad_pcb'
CACHE=ROOT/'.cache/routing'
CACHE.mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser()
parser.add_argument('action',choices=['plane','export','import','pads'])
parser.add_argument('--session',type=Path,default=CACHE/'result.ses')
parser.add_argument('--dsn',type=Path,default=CACHE/'input.dsn')
parser.add_argument('--board',type=Path,default=TARGET,help='Candidate PCB to read or update; defaults to the working board.')
parser.add_argument('--signal-routing','--three-signal-layers',dest='signal_routing',action='store_true',help='Omit the provisional L3 ground pour from signal routing interchange.')
parser.add_argument('--replace-tracks',action='store_true',help='Replace generated routing while retaining fixed copper omitted by SES; use the matching DSN base and back it up first.')
parser.add_argument('--fresh-routing',action='store_true',help='Export placement and fixed copper without provisional generated tracks.')
parser.add_argument('--outer-ground',action='store_true',help='Add outer-layer ground pours for a separately checked candidate.')
parser.add_argument('--quiet',action='store_true')
args=parser.parse_args()
TARGET=args.board.resolve()
args.dsn=args.dsn.resolve()
args.session=args.session.resolve()
load_path=TARGET
original=loads(TARGET.read_text(encoding='utf-8'))
def fixed(n):
    value=first(n,'locked')
    return value is not None and (len(value)==1 or value[1]=='yes')
fixed_ids={first(n,'uuid')[1] for n in original if isinstance(n,list) and n[0] in {'segment','via','arc'} and fixed(n)}
def copper_signature(n):
    keys=['start','end','mid','width','layer','net'] if n[0]!='via' else ['at','size','drill','layers','net']
    def atom(v):
        try:return round(float(v),6)
        except ValueError:return str(v)
    return tuple((k,tuple(atom(v) for v in first(n,k)[1:])) for k in keys if first(n,k))
fixed_before={first(n,'uuid')[1]:copper_signature(n) for n in original if isinstance(n,list) and n[0] in {'segment','via','arc'} and fixed(n)}
strip_tracks=(args.action=='export' and args.fresh_routing) or (args.action=='import' and args.replace_tracks)
strip_plane=args.action=='export' and args.signal_routing
strip_outer=args.action=='export'
if strip_tracks or strip_plane or strip_outer:
    # Removing large SWIG-owned collections in this KiCad build destabilizes
    # subsequent object iteration. Filter the native file before loading it;
    # the original candidate remains untouched until an explicit import/save.
    data=original
    data[:]=[n for n in data if not (isinstance(n,list) and (
        (strip_tracks and n[0] in {'segment','via','arc'} and not fixed(n)) or
        (n[0]=='zone' and not first(n,'keepout') and first(n,'layer') and (
            (strip_plane and first(n,'layer')[1]=='In2.Cu') or
            (strip_outer and first(n,'layer')[1] in {'F.Cu','B.Cu'})))))]
    load_path=CACHE/(TARGET.stem+'-interchange-base.kicad_pcb')
    load_path.write_text(dumps(data)+'\n',encoding='utf-8',newline='\n')
board=load_board(load_path,OUT/'flight-computer.kicad_pro')
board.SetFileName(str(TARGET))

if args.action=='plane':
    planes=[(pcbnew.In1_Cu,'L2 ground reference'),(pcbnew.In2_Cu,'L3 ground reference')]
    if args.outer_ground:planes.extend([(pcbnew.F_Cu,'Top ground pour'),(pcbnew.B_Cu,'Bottom ground pour')])
    for layer,name in planes:
        if any(z.GetZoneName()==name for z in board.Zones()):continue
        z=pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(board.FindNet('GND'))
        z.SetZoneName(name)
        z.SetLocalClearance(pcbnew.FromMM(.2))
        z.SetMinThickness(pcbnew.FromMM(.15))
        z.SetThermalReliefGap(pcbnew.FromMM(.2))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        outline=z.Outline();outline.NewOutline()
        for x,y in [(100.3,100.3),(150.5,100.3),(150.5,122.56),(100.3,122.56)]:
            outline.Append(pcbnew.FromMM(x),pcbnew.FromMM(y))
        board.Add(z)
    save_board(board,TARGET)
    print('Added ground reference zones; refill before export.')
elif args.action=='export':
    board.BuildConnectivity()
    if not pcbnew.ExportSpecctraDSN(board,str(args.dsn)):
        raise SystemExit('DSN export failed')
    print('Exported',args.dsn)
elif args.action=='import':
    if not pcbnew.ImportSpecctraSES(board,str(args.session)):
        raise SystemExit('SES import failed')
    board.BuildConnectivity()
    for item in board.GetDrawings():
        if isinstance(item,pcbnew.PCB_TEXT) and 'UNROUTED PLACEMENT' in item.GetText():
            item.SetText('ROUTING IN PROGRESS — NOT FOR FABRICATION')
    save_board(board,TARGET)
    saved=loads(TARGET.read_text(encoding='utf-8'))
    saved_ids={first(n,'uuid')[1] for n in saved if isinstance(n,list) and n[0] in {'segment','via','arc'}}
    missing=fixed_ids-saved_ids
    if missing:raise SystemExit(f'SES import lost {len(missing)} fixed copper items')
    saved_fixed={first(n,'uuid')[1]:copper_signature(n) for n in saved if isinstance(n,list) and n[0] in {'segment','via','arc'} and first(n,'uuid')[1] in fixed_ids}
    changed=[key for key in fixed_ids if fixed_before[key]!=saved_fixed[key]]
    if changed:raise SystemExit(f'SES import changed {len(changed)} fixed copper geometries/nets')
    (ROOT/'reports/pcb/fixed-copper-check.json').write_text(json.dumps({'status':'pass','board':TARGET.name,
        'session':args.session.name,'fixed_items_checked':len(fixed_ids),'geometry_width_layer_and_net_preserved':True},indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Preserved {len(fixed_ids)} fixed copper items omitted by SES.')
    print('Imported session:',args.session)
    print('Track/via items:',len(board.GetTracks()))
elif args.action=='pads':
    nets={'D+','D-','USB_D+','USB_D-','BASE_N_5','BASE_N_6','BASE_N_7','VCORE','LX'}
    rows=[]
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() in nets:
                pos=p.GetPosition()
                rows.append({'ref':fp.GetReference(),'pad':p.GetNumber(),'net':p.GetNetname(),
                    'x':round(pcbnew.ToMM(pos.x),6),'y':round(pcbnew.ToMM(pos.y),6),
                    'copper_layers':[board.GetLayerName(l) for l in p.GetLayerSet().CuStack()]})
    (ROOT/'reports/pcb/critical-pads.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8',newline='\n')
    if not args.quiet:print(json.dumps(rows,indent=2))
    placements=[]
    for fp in board.GetFootprints():
        if fp.GetReference().startswith('H'):continue
        pos=fp.GetPosition()
        placements.append({'ref':fp.GetReference(),'x':round(pcbnew.ToMM(pos.x)-100,6),
            'y':round(122.86-pcbnew.ToMM(pos.y),6),'rotation':fp.GetOrientationDegrees(),
            'side':'B' if fp.GetLayer()==pcbnew.B_Cu else 'F','footprint':fp.GetFPID().GetUniStringLibId()})
    (ROOT/'reports/pcb/placement-current.json').write_text(json.dumps({'status':'routing development; not released',
        'placements':placements},indent=2)+'\n',encoding='utf-8',newline='\n')
