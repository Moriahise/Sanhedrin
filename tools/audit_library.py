"""Assertions against original repository data, not the migration implementation."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sanhedrin.store import Store
from sanhedrin.locking import writer_lock
from sanhedrin.model import canonical_json,date_value
from sanhedrin.migrate import migrate

def audit(store,root,repeat=False):
    baseline=[]
    for p in sorted((root/'data/questions/chunks').glob('qa_*.json')):baseline+=json.loads(p.read_text())['questions']
    errors=store.verify();missing=[q['id'] for q in baseline if not store.get(q['id'])]
    assert not errors and not missing,(errors[:10],missing[:10])
    old_aliases=json.loads((root/'data/questions/aliases.json').read_text())['aliases']
    missing_aliases=[a for a,ref in old_aliases.items() if ref['id'] not in store.resolve(a)]
    assert not missing_aliases,missing_aliases[:10]
    file='data/qa/12yeshiva-qa-database-2026-01-23.json';first=json.loads((root/file).read_text());rows=first['questions'];found=[]
    for q in rows:
        native=str(q['id']);ids=store.resolve(native,file);matching=[store.get(i) for i in ids if store.get(i)['provider']=='yeshiva' and store.get(i)['native_id']==native]
        assert len(matching)==1,(native,ids)
        value=matching[0];assert value['url']==q['url'],native
        assert any(c.get('path')==file and c.get('date')==date_value(first['exported_at']) for c in value['import_charges']),native
        found.append(value['id'])
    assert len(rows)==246 and len(set(found))==246
    documents=[q for q in store.records() if q['kind']=='document'];assert len(documents)==17
    before=store.logical_hash()
    if repeat:
        migrate(store,root);assert store.logical_hash()==before,'Repeated migration changed logical state'
    return {'baseline_ids_verified':len(baseline),'original_aliases_verified':len(old_aliases),'first_2026_yeshiva_upload_verified':len(found),'documents':len(documents),'total':store.count(),'provider_counts':dict(store.db.execute('SELECT provider,count(*) FROM records GROUP BY provider')),'logical_hash':before,'repeat_migration_unchanged':repeat,'errors':errors}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--db',type=Path,default=Path('.sanhedrin/library.sqlite'));p.add_argument('--report',type=Path,default=Path('test-results/audit.json'));p.add_argument('--repeat',action='store_true');args=p.parse_args()
    with writer_lock(args.db.parent/'publisher.lock'),Store(args.db) as store:result=audit(store,args.root,args.repeat)
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,indent=2))
