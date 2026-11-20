"""Record the candidate stackup and selective exposed-pad via treatment.

These are quotation requirements, subject to fabricator confirmation. Running
this script does not release the board for manufacture or verify impedance.
"""
import argparse
import json
from pathlib import Path
from kicad_sexpr import loads,dumps,first,children,Quoted as Q
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--board',type=Path,required=True)
parser.add_argument('--ep-report',type=Path,required=True)
parser.add_argument('--report',type=Path,default=ROOT/'reports/pcb/fabrication-settings.json')
args=parser.parse_args()
b=loads(args.board.read_text(encoding='utf-8'))
layer_count=sum(1 for n in first(b,'layers') if isinstance(n,list) and str(n[1]).endswith('.Cu'))
if layer_count not in (4,6):raise ValueError('Only the reviewed four- and six-layer candidates are supported')
setup=first(b,'setup')
stack=['stackup']
def layer(name,kind,thickness=None,material=None,er=None):
    n=['layer',Q(name),['type',Q(kind)]]
    if thickness is not None:n.append(['thickness',str(thickness)])
    if material:n.append(['material',Q(material)])
    if er:n.append(['epsilon_r',str(er)])
    stack.append(n)
layer('F.SilkS','Top Silk Screen')
layer('F.Mask','Top Solder Mask',.01524,er=3.8)
layer('F.Cu','copper',.035)
layer('dielectric 1','prepreg',.0994,'3313',4.1)
layer('In1.Cu','copper',.0152)
if layer_count==6:
    layer('dielectric 2','core',.1,'FR4',4.6)
    layer('In2.Cu','copper',.0152)
    layer('dielectric 3','core',1.1208,'7628 / 0.7-mm unclad FR4 / 7628',4.6)
    layer('In3.Cu','copper',.0152)
    layer('dielectric 4','core',.1,'FR4',4.6)
    layer('In4.Cu','copper',.0152)
    layer('dielectric 5','prepreg',.0994,'3313',4.1)
else:
    layer('dielectric 2','core',1.265,'FR4',4.6)
    layer('In2.Cu','copper',.0152)
    layer('dielectric 3','prepreg',.0994,'3313',4.1)
layer('B.Cu','copper',.035)
layer('B.Mask','Bottom Solder Mask',.01524,er=3.8)
layer('B.SilkS','Bottom Silk Screen')
stack.extend([['copper_finish',Q('ENIG')],['dielectric_constraints','yes']])
setup[:]=[n for n in setup if not (isinstance(n,list) and n[0]=='stackup')]
setup.insert(1,stack)
ep=json.loads(args.ep_report.read_text(encoding='utf-8'))['processor_exposed_pad_vias']
if len(ep)!=3:raise ValueError('Expected exactly three reviewed processor exposed-pad vias')
selected=[]
for v in children(b,'via'):
    at=first(v,'at');x,y=map(float,at[1:3])
    if not any(abs(x-p['x'])<.001 and abs(y-p['y'])<.001 for p in ep):continue
    if first(v,'net')[1]!='GND':raise ValueError('Exposed-pad via is not ground')
    for key in ('filling','capping','tenting'):
        v[:]=[n for n in v if not (isinstance(n,list) and n[0]==key)]
    v.extend([['filling','yes'],['capping','yes'],['tenting',['front','no'],['back','yes']]])
    selected.append({'x':x,'y':y,'uuid':first(v,'uuid')[1]})
if len(selected)!=3:raise ValueError('Exposed-pad via coordinates do not match this PCB')
if layer_count==6:first(first(b,'general'),'thickness')[1]='1.68088'
args.board.write_text(dumps(b)+'\n',encoding='utf-8',newline='\n')
stack_name='JLC06161H-3313E' if layer_count==6 else 'JLC04161H-3313'
result={'status':'candidate fabrication requirements; supplier confirmation pending',
        'manufacturing_release':False,'board':args.board.name,'stackup':stack_name,'copper_layers':layer_count,
        'source':'https://jlcpcb.com/impedance','nominal_board_thickness_mm':1.6,
        'copper_and_dielectric_sum_mm':1.6504 if layer_count==6 else 1.5642,'sum_including_modelled_mask_mm':1.68088 if layer_count==6 else 1.59468,
        'internal_dielectric_Dk_assumed':4.6,'internal_dielectric_Dk_supplier_confirmed':False,
        'ordinary_vias':'tented both faces per board defaults',
        'processor_vias':selected,'processor_via_process':'epoxy filled and copper capped; exposed on front, tented on back',
        'impedance_verified':False,'limits':'Fabricator must confirm materials, finished copper, tolerances and USB geometry. Include a selective via-treatment drawing with any quotation/manufacturing package.'}
args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
if args.board.resolve()==(ROOT/'hardware/rev-a/flight-computer.kicad_pcb').resolve():
    (ROOT/'hardware/rev-a/layout-settings.json').write_text(json.dumps({'copper_layers':layer_count,'candidate_stackup':stack_name},indent=2)+'\n',encoding='utf-8',newline='\n')
print('Recorded candidate stackup and three selective filled/capped vias; supplier confirmation remains required.')
