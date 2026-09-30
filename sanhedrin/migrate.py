"""Non-destructive, repeatable migration of all published IDs and raw archives."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from bs4 import BeautifulSoup
from .model import DataError,normalize,digest,canonical_json,legacy_context,date_value

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def extract_items(data):
    if isinstance(data,list):return data
    if isinstance(data,dict):
        for key in ('questions','items','records','entries','data','qa'):
            if isinstance(data.get(key),list):return data[key]
    raise DataError('Unsupported import root; expected a records array')

def aliases_for(store,q,raw,context=''):
    pid=q['id'];native=q['native_id'];legacy=raw.get('legacy') or {};sid=raw.get('source_id') or raw.get('id') or legacy.get('source_id')
    for alias in {str(sid or ''),native,'n'+native}:store.alias(alias,pid,context)
    if q['provider']=='miyodeya':
        for alias in ('my-'+native,'miyodeya_'+native):store.alias(alias,pid)
    if legacy.get('src'):
        for alias in {str(sid or ''),native,'n'+native}:store.alias(alias,pid,legacy_context(legacy['src']))
    if legacy.get('old_file'):
        params=parse_qs(urlsplit(legacy['old_file']).query);store.alias(params.get('id',[''])[0],pid,legacy_context(params.get('src',[''])[0]));store.alias(legacy['old_file'],pid)

def bootstrap(store,root):
    if store.db.execute("SELECT 1 FROM metadata WHERE key='baseline_complete'").fetchone():return {'baseline':store.db.execute('SELECT count(*) FROM baseline').fetchone()[0],'already_complete':True}
    paths=sorted((root/'data/questions/chunks').glob('qa_*.json'))
    if not paths:raise DataError('No current question chunks; refusing an empty bootstrap')
    count=0
    with store.transaction():
        for p in paths:
            data=json.loads(p.read_text());rows=data.get('questions')
            if not isinstance(rows,list) or data.get('count')!=len(rows):raise DataError('Invalid chunk count: '+str(p))
            for raw in rows:
                q=normalize(raw,public_id=raw['id'],preserve=True);store.insert(q,baseline=raw);aliases_for(store,q,raw);count+=1
        expected=json.loads((root/'data/questions/manifest.json').read_text())['total']
        if count!=expected:raise DataError(f'Baseline count mismatch: {count} != {expected}')
        aliases=json.loads((root/'data/questions/aliases.json').read_text()).get('aliases',{})
        for alias,ref in aliases.items():
            if not isinstance(ref,dict) or not store.get(ref.get('id')):raise DataError('Broken existing alias: '+alias)
            store.alias(alias,ref['id'])
        store.db.execute("INSERT INTO metadata VALUES('baseline_complete',?)",(str(count),))
    return {'baseline':count,'already_complete':False}

def import_file(store,path,root):
    origin=path.relative_to(root).as_posix();sha=sha256_file(path)
    prior=store.db.execute('SELECT sha256,report FROM imports WHERE path=?',(origin,)).fetchone()
    if prior and prior[0]==sha:
        report=json.loads(prior[1]);return {'path':origin,'status':'already_imported','records':report['records'],'inserted':0,'updated':0,'unchanged':report['records'],'quarantined':report.get('quarantined',0)}
    data=json.loads(path.read_text());rows=extract_items(data);meta=data if isinstance(data,dict) else {};counts=Counter();hint=meta.get('provider','')
    if origin.startswith('miyodea/'):hint='miyodeya'
    with store.transaction():
        for ordinal,raw in enumerate(rows,1):
            h=store.archive(raw,origin)
            try:
                q=normalize(raw,default_provider=hint,exported_at=meta.get('exported_at'),allow_reference=True)
                outcome,ids=store.upsert(q,mode='enrich',reason=origin);counts[outcome]+=1
                for pid in ids:
                    target=store.get(pid);aliases_for(store,target,raw,origin)
                    if meta.get('exported_at'):
                        charge={'path':origin,'date':date_value(meta['exported_at'])};charges=target.setdefault('import_charges',[])
                        if charge not in charges:old=store.get(pid);charges.append(charge);store.update(old,target,'import charge')
            except DataError as e:store.db.execute('INSERT OR IGNORE INTO quarantine VALUES(?,?,?,?)',(origin,ordinal,str(e),h));counts['quarantined']+=1
        report={'path':origin,'sha256':sha,'records':len(rows),**dict(counts)}
        store.db.execute('INSERT INTO imports VALUES(?,?,?) ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256,report=excluded.report',(origin,sha,canonical_json(report)))
    return report

def import_documents(store,root):
    index=json.loads((root/'responsa.json').read_text()) if (root/'responsa.json').exists() else []
    entries={r['file']:r for r in index if isinstance(r,dict) and str(r.get('file','')).startswith('responsa/')}
    for p in (root/'responsa').rglob('*.html'):entries.setdefault(p.relative_to(root).as_posix(),{'title_he':p.stem,'title_en':p.stem})
    counts=Counter()
    for rel,meta in sorted(entries.items()):
        path=(root/rel).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():raise DataError('Missing/unsafe document: '+rel)
        sha=sha256_file(path);prior=store.db.execute('SELECT sha256 FROM imports WHERE path=?',(rel,)).fetchone()
        if prior and prior[0]==sha:counts['unchanged']+=1;continue
        soup=BeautifulSoup(path.read_text(),'html.parser')
        for node in soup.select('script,style,nav,header,footer,template,iframe,svg,math'):node.decompose()
        content=soup.select_one('.content') or soup.find('main') or soup.body or soup
        for node in content.select('[data-tooltip]'):node.append(' ['+str(node.get('data-tooltip'))+']')
        pid='doc-'+digest(rel)[:20]
        q=normalize({'id':pid,'provider':'local','native_id':rel,'title':meta.get('title_he') or meta.get('title_en') or path.stem,'title_en':meta.get('title_en',''),'title_he':meta.get('title_he',''),'question':content.get_text('\n',strip=True),'answers':[],'kind':'document','format':'plain','document_path':rel,'document_sha256':sha,'published_at':date_value(meta.get('date')),'category':'general','needs_review':True},public_id=pid)
        with store.transaction():
            old=store.get(pid)
            outcome=('updated' if store.update(old,q,'document changed') else 'unchanged') if old else 'inserted'
            if not old:store.insert(q)
            store.alias(rel,pid);store.db.execute('INSERT INTO imports VALUES(?,?,?) ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256,report=excluded.report',(rel,sha,canonical_json({'document':True})))
        counts[outcome]+=1
    return {'documents':len(entries),**dict(counts)}

def migrate(store,root):
    root=root.resolve();baseline=bootstrap(store,root)
    files=set((root/'data/qa').rglob('*.json'))|set((root/'miyodea').rglob('*.json'))|set((root/'qa_db').rglob('*.json'))
    if (root/'qa_db.json').exists():files.add(root/'qa_db.json')
    reports=[import_file(store,p,root) for p in sorted(files) if not p.name.endswith(('_split_manifest.json','_manifest.json'))]
    documents=import_documents(store,root)
    with store.transaction():
        for r in store.db.execute("SELECT public_id,native_id FROM records WHERE provider IN ('miyodeya','yeshiva','chabad')"):
            if r['native_id'].isdigit():store.alias(r['native_id'],r['public_id'])
    errors=store.verify()
    if errors:raise DataError('; '.join(errors[:10]))
    counts=sum((Counter({k:r.get(k,0) for k in ('inserted','updated','unchanged','quarantined')}) for r in reports),Counter())
    return {'baseline':baseline,'total':store.count(),'provider_counts':dict(store.db.execute('SELECT provider,count(*) FROM records GROUP BY provider')),'documents':documents,'imports':reports,'counts':dict(counts),'logical_hash':store.logical_hash(),'verification_errors':errors}
