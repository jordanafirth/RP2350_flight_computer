"""Remove reported dead ends only after every signal is connected.

Use on a scratch copy, followed by native DRC. Preserve the three selectively
filled/capped processor ground vias, even if the report lists a dead end.
"""
import argparse,json
from pathlib import Path
from kicad_sexpr import loads,dumps,first
p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
r=json.loads(a.report.read_text(encoding='utf-8'))
if any(any('[GND]' not in i['description'] for i in c['items']) for c in r['unconnected_items']):raise SystemExit('Connect all signals before pruning completed routing')
if any(v['type'] not in {'npth_inside_courtyard','track_dangling','via_dangling'} for v in r['violations']):raise SystemExit('Resolve physical violations before pruning')
d=loads(a.board.read_text(encoding='utf-8'))
protected={first(n,'uuid')[1] for n in d if isinstance(n,list) and n[0]=='via' and first(n,'filling') and first(n,'filling')[1]=='yes'}
remove={i['uuid'] for v in r['violations'] if v['type'] in {'track_dangling','via_dangling'} for i in v['items'] if i['uuid'] not in protected}
if not remove:print('No removable dead ends');raise SystemExit(0)
d[:]=[n for n in d if not (isinstance(n,list) and n[0] in {'segment','via','arc'} and first(n,'uuid')[1] in remove)]
a.board.write_text(dumps(d)+'\n',encoding='utf-8',newline='\n');print('Removed',len(remove),'reported dead ends')
