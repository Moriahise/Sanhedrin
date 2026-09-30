import argparse
import json
from pathlib import Path
from .model import DataError
from .store import Store
from .locking import writer_lock

def main():
    parser=argparse.ArgumentParser(description='Sanhedrin durable library publisher');parser.add_argument('--root',type=Path,default=Path('.'));parser.add_argument('--db',type=Path,default=Path('.sanhedrin/library.sqlite'));parser.add_argument('--report',type=Path)
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('migrate','verify','status'):commands.add_parser(name)
    p=commands.add_parser('build');p.add_argument('--output',type=Path,default=Path('dist'));p.add_argument('--max-bytes',type=int,default=900_000_000)
    p=commands.add_parser('verify-export');p.add_argument('--output',type=Path,default=Path('dist'))
    p=commands.add_parser('sync');p.add_argument('--config',type=Path,default=Path('config/sources.json'));p.add_argument('--source',choices=['miyodeya','yeshiva','din','aish','chabad'])
    p=commands.add_parser('snapshot');p.add_argument('--directory',type=Path,required=True)
    for name in ('restore','restore-release'):
        p=commands.add_parser(name);p.add_argument('--directory',type=Path,required=True);p.add_argument('--minimum-total',type=int,default=63051)
        if name=='restore-release':p.add_argument('--repo',required=True)
    p=commands.add_parser('publish-snapshot');p.add_argument('--directory',type=Path,required=True);p.add_argument('--repo',required=True);p.add_argument('--commit',required=True)
    args=parser.parse_args();exit_code=0
    try:
        with writer_lock(args.db.parent/'publisher.lock'):
            if args.command=='restore':
                from .snapshot import restore
                result=restore(args.directory,args.db,minimum_total=args.minimum_total)
            elif args.command=='restore-release':
                from .releases import restore_release
                result=restore_release(args.repo,args.directory,args.db,minimum_total=args.minimum_total)
            elif args.command=='publish-snapshot':
                from .releases import publish_snapshot
                result=publish_snapshot(args.repo,args.directory,args.commit)
            elif args.command=='verify-export':
                from .build import verify_export
                result=verify_export(args.output)
            else:
                with Store(args.db) as store:
                    if args.command=='migrate':
                        from .migrate import migrate
                        result=migrate(store,args.root)
                    elif args.command=='build':
                        from .build import build
                        if store.verify():raise DataError('Database verification failed')
                        result=build(store,args.root,args.output,max_bytes=args.max_bytes)
                    elif args.command=='verify':
                        errors=store.verify();result={'total':store.count(),'errors':errors,'logical_hash':store.logical_hash()}
                        if errors:exit_code=1
                    elif args.command=='status':
                        from .status import status
                        result=status(store)
                    elif args.command=='snapshot':
                        from .snapshot import snapshot
                        result=snapshot(store,args.directory)
                    else:
                        from .collectors import sync
                        from .config import load_config
                        if not store.db.execute('SELECT count(*) FROM baseline').fetchone()[0]:raise DataError('Migrate the baseline before collecting')
                        result=sync(store,load_config(args.config),source=args.source);exit_code=2 if result['status']=='partial' else 0
    except (DataError,OSError,ValueError) as e:result={'status':'error','reason':str(e)};exit_code=1
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2));return exit_code
if __name__=='__main__':raise SystemExit(main())
