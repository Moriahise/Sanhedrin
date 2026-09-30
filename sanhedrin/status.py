import json
from .model import utcnow
def status(store):
    health=[dict(r)|{'report':json.loads(r['report'])} for r in store.db.execute('SELECT run_id,started_at,finished_at,status,report FROM runs ORDER BY started_at DESC LIMIT 20')]
    checks=[dict(r) for r in store.db.execute('SELECT provider,state,count(*) AS count,max(checked_at) AS last_checked_at FROM source_state GROUP BY provider,state')]
    return {'schema':1,'generated_at':utcnow(),'total':store.count(),'providers':dict(store.db.execute('SELECT provider,count(*) FROM records GROUP BY provider')),'runs':health,'source_checks':checks,'quarantined_raw_records':store.db.execute('SELECT count(*) FROM quarantine').fetchone()[0],'note':'Local answers and remote counts differ until a complete source check. Failed checks preserve published content.'}
