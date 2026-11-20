"""Write explicit prototype routing defaults without changing user-wide settings."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'hardware/rev-a/flight-computer.kicad_pro'
data=json.loads(p.read_text())
data.setdefault('board',{}).setdefault('design_settings',{}).setdefault('rules',{}).update({
    'min_clearance':.1, 'min_copper_edge_clearance':.25,
    'min_track_width':.1, 'min_via_diameter':.4,
    'min_through_hole_diameter':.2, 'min_via_annular_width':.1,
    'min_hole_clearance':.2, 'min_hole_to_hole':.2,
})
base={'name':'Default','clearance':.1,'track_width':.1,'via_diameter':.4,'via_drill':.2,
      'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.13,'diff_pair_gap':.13,
      'diff_pair_via_gap':.25,'wire_width':6,'bus_width':12,'line_style':0,
      'pcb_color':'rgba(0, 0, 0, 0.000)','schematic_color':'rgba(0, 0, 0, 0.000)',
      'priority':2147483647}
power=dict(base,name='Power',track_width=.4,clearance=.2,priority=0)
logic=dict(base,name='Logic supply',track_width=.15,priority=1)
core=dict(base,name='Core supply',track_width=.2,priority=2)
data['net_settings']={'meta':{'version':4},'classes':[base,power,logic,core],
    'netclass_assignments':{},'netclass_patterns':[
        {'netclass':'Power','pattern':net} for net in ['VBAT*','VBUS','VSYS']]+[
        {'netclass':'Logic supply','pattern':'+3V3'},{'netclass':'Core supply','pattern':'VCORE'}],
    'net_colors':None}
p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Configured 0.10-mm signals, 0.40/0.20-mm vias, and separate 0.15/0.20/0.40-mm supply classes.')
