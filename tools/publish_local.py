"""Always-on host publisher with durable state and atomic current symlink."""
import argparse
import json
import os
import sys
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sanhedrin.store import Store
from sanhedrin.locking import writer_lock
from sanhedrin.migrate import migrate
from sanhedrin.collectors import sync
from sanhedrin.config import load_config
from sanhedrin.build import build,verify_export
from sanhedrin.snapshot import snapshot
from sanhedrin.model import DataError

def publish(root,state,public):
    run=uuid.uuid4().hex;state.mkdir(parents=True,exist_ok=True);public.mkdir(parents=True,exist_ok=True);reports=state/'reports';reports.mkdir(exist_ok=True)
    with writer_lock(state/'publisher.lock'),Store(state/'library.sqlite') as store:
        migration=migrate(store,root);sources=sync(store,load_config(root/'config/sources.json'));errors=store.verify()
        if errors:raise DataError('Post-collection verification failed')
        directory=public/'versions'/run;manifest=build(store,root,directory);verification=verify_export(directory);backup=snapshot(store,state/'snapshots'/run)
        pointer=public/('.current-'+run);pointer.symlink_to(Path('versions')/run,target_is_directory=True);os.replace(pointer,public/'current')
        report={'migration':{'total':migration['total']},'sync':sources,'build':manifest,'verification':verification,'snapshot':backup};(reports/(run+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));temporary=reports/'.latest-run.json';temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2));os.replace(temporary,reports/'latest-run.json');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--state',type=Path,required=True);p.add_argument('--public',type=Path,required=True);args=p.parse_args()
    try:result=publish(args.root.resolve(),args.state.resolve(),args.public.resolve());print(json.dumps(result,ensure_ascii=False));raise SystemExit(2 if result['sync']['status']=='partial' else 0)
    except (DataError,OSError,ValueError) as e:print(json.dumps({'status':'error','reason':str(e)}));raise SystemExit(1)
