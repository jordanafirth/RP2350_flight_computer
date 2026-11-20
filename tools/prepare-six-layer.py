"""Compare a six-layer scratch board with adjacent ground on both outer faces."""
import copy
import uuid
from pathlib import Path
from kicad_sexpr import loads,dumps,first,children,Quoted as Q
from native_cad import pcbnew,load_board,save_board
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hardware/rev-a';CACHE=ROOT/'.cache/routing'
path=CACHE/'candidate-six-placement.kicad_pcb'
b=loads((CACHE/'candidate-offset.kicad_pcb').read_text(encoding='utf-8'))
layers=first(b,'layers');index=next(i for i,n in enumerate(layers) if isinstance(n,list) and n[1]=='B.Cu')
layers[index:index]=[['8',Q('In3.Cu'),'signal'],['10',Q('In4.Cu'),'power']]
source_ground=next(z for z in children(b,'zone') if first(z,'name') and first(z,'name')[1]=='L2 ground reference')
z=copy.deepcopy(source_ground)
z[:]=[n for n in z if not (isinstance(n,list) and n[0]=='filled_polygon')]
first(z,'layer')[1]=Q('In4.Cu');first(z,'name')[1]=Q('L5 ground reference');first(z,'uuid')[1]=Q(str(uuid.uuid4()))
b.append(z)
edge=[]
for z in children(b,'zone'):
    if first(z,'layer')[1]!='In2.Cu' or not first(z,'keepout'):continue
    if first(z,'name') and first(z,'name')[1].startswith('USB return reference'):
        first(z,'layer')[1]=Q('In4.Cu')
    else:edge.append(z)
for layer in ('In3.Cu','In4.Cu'):
    for original in edge:
        z=copy.deepcopy(original);first(z,'layer')[1]=Q(layer);first(z,'uuid')[1]=Q(str(uuid.uuid4()));b.append(z)
path.write_text(dumps(b)+'\n',encoding='utf-8',newline='\n')
native=load_board(path,OUT/'flight-computer.kicad_pro')
if native.GetCopperLayerCount()!=6:raise ValueError('Six copper layers were not enabled')
save_board(native,path)
print('Prepared six-layer comparison with L2 and L5 ground reference planes:',path)
