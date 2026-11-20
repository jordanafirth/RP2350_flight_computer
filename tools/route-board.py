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
parser.add_argument('--three-signal-layers',action='store_true')
parser.add_argument('--replace-tracks',action='store_true',help='Replace this generated candidate routing from a full-board SES; back up the PCB first.')
parser.add_argument('--fresh-routing',action='store_true',help='Export placement without existing candidate tracks.')
parser.add_argument('--outer-ground',action='store_true',help='Add outer-layer ground pours for a separately checked candidate.')
parser.add_argument('--quiet',action='store_true')
args=parser.parse_args()
TARGET=args.board.resolve()
args.dsn=args.dsn.resolve()
args.session=args.session.resolve()
load_path=TARGET
strip_tracks=(args.action=='export' and args.fresh_routing) or (args.action=='import' and args.replace_tracks)
strip_plane=args.action=='export' and args.three_signal_layers
if strip_tracks or strip_plane:
    # Removing large SWIG-owned collections in this KiCad build destabilizes
    # subsequent object iteration. Filter the native file before loading it;
    # the original candidate remains untouched until an explicit import/save.
    data=loads(TARGET.read_text(encoding='utf-8'))
    data[:]=[n for n in data if not (isinstance(n,list) and (
        (strip_tracks and n[0] in {'segment','via','arc'}) or
        (strip_plane and n[0]=='zone' and first(n,'layer') and first(n,'layer')[1]=='In2.Cu')))]
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
