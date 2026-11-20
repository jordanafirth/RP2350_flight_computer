"""Adopt the checked fine candidate and apply the reviewed USB placement fix.

Preserves the previous working board in ignored local history. USB copper is
deliberately removed for rerouting; all other candidate copper is retained.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from kicad_sexpr import loads,dumps,children,first
from native_cad import pcbnew,load_board,save_board

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/rev-a'
target=OUT/'flight-computer.kicad_pcb'
candidate=ROOT/'.cache/routing/candidate-fine.kicad_pcb'
backup=ROOT/'.cache/routing'/('working-before-usb-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.kicad_pcb')
shutil.copy2(target,backup)
data=loads(candidate.read_text(encoding='utf-8'))
usb={'D+','D-','USB_D+','USB_D-','SERVO3'}
removed=0
filtered=[]
for n in data:
    if isinstance(n,list) and n[0] in {'segment','via','arc'} and first(n,'net')[1] in usb:
        removed+=1
        continue
    if isinstance(n,list) and n[0]=='footprint':
        ref=next(p[2] for p in children(n,'property') if p[1]=='Reference')
        if ref in {'TP1','TP2'}:continue
    filtered.append(n)
scratch=ROOT/'.cache/routing/usb-adjustment.kicad_pcb'
scratch.write_text(dumps(filtered)+'\n',encoding='utf-8',newline='\n')
board=load_board(scratch,OUT/'flight-computer.kicad_pro')
sites=json.loads((ROOT/'.cache/usb-placement-options.json').read_text())['resistors']
for fp in board.GetFootprints():
    if fp.GetReference() not in sites:continue
    p=sites[fp.GetReference()]
    if fp.GetLayer()==pcbnew.B_Cu:fp.Flip(fp.GetPosition(),pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(p['rotation'])
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100+p['x']),pcbnew.FromMM(122.86-p['y'])))
    fp.Reference().SetLayer(pcbnew.F_Fab)
resistor_boxes=[]
for fp in board.GetFootprints():
    if fp.GetReference() not in {'R9','R10'}:continue
    for pad in fp.Pads():
        box=pad.GetBoundingBox()
        resistor_boxes.append((box.GetX()-pcbnew.FromMM(.15),box.GetY()-pcbnew.FromMM(.15),
            box.GetX()+box.GetWidth()+pcbnew.FromMM(.15),box.GetY()+box.GetHeight()+pcbnew.FromMM(.15)))
ripup=set()
for track in board.GetTracks():
    if pcbnew.F_Cu not in track.GetLayerSet().CuStack():continue
    b=track.GetBoundingBox()
    if any(a<b.GetX()+b.GetWidth() and c>b.GetX() and low<b.GetY()+b.GetHeight() and high>b.GetY() for a,low,c,high in resistor_boxes):
        ripup.add(track.m_Uuid.AsString())
# Explicit edge keepouts compensate for DSN's default boundary clearance.
# Pads and pours are allowed; new tracks and vias stay at least 0.30 mm in.
for layer in (pcbnew.F_Cu,pcbnew.In2_Cu,pcbnew.B_Cu):
    for i,(x1,y1,x2,y2) in enumerate([(100,100,150.8,100.3),(100,122.56,150.8,122.86),(100,100,100.3,122.86),(150.5,100,150.8,122.86)]):
        z=pcbnew.ZONE(board);z.SetLayer(layer);z.SetIsRuleArea(True)
        z.SetZoneName('Routing edge margin '+board.GetLayerName(layer)+' '+str(i))
        z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False)
        outline=z.Outline();outline.NewOutline()
        for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:outline.Append(pcbnew.FromMM(x),pcbnew.FromMM(y))
        board.Add(z)
board.SetFileName(str(target))
save_board(board,target)
updated=loads(target.read_text(encoding='utf-8'))
updated[:]=[n for n in updated if not (isinstance(n,list) and n[0] in {'segment','via','arc'} and first(n,'uuid')[1] in ripup)]
target.write_text(dumps(updated)+'\n',encoding='utf-8',newline='\n')
# Keep generation coordinates aligned with the selected, checked placements.
overrides=OUT/'placement-overrides.json'
positions=json.loads(overrides.read_text())
for ref,p in sites.items():positions[ref]={'x':p['x'],'y':p['y']}
overrides.write_text(json.dumps(positions,indent=2)+'\n',encoding='utf-8',newline='\n')
print(f'Adopted candidate; moved R9/R10, removed two USB test stubs, {removed} USB/servo copper items and {len(ripup)} obstructing items for rerouting.')
print('Previous working PCB:',backup)
