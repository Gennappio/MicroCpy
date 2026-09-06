#!/usr/bin/env python3
"""Prepare once, then run/retry/replay a saved Planner manifest from GUI or CLI."""
import argparse
import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.workflow.replication import (REPO, add_replicates, batch_status, compile_plan,
    create_batch, execute_batch, read_json, summarize_batch)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow', type=Path, action='append', default=[])
    parser.add_argument('--suite', type=Path, help='Prepare all p53_sa_*.json files together (deduplicates baselines)')
    parser.add_argument('--runs-dir', type=Path, default=REPO / 'runs')
    parser.add_argument('--prepare', action='store_true', help='Save the plan without launching simulations')
    parser.add_argument('--preview', action='store_true', help='Print resolved identities without saving or running')
    parser.add_argument('--replicates', type=int, help='Override default replicate count when preparing')
    parser.add_argument('--master-seed', help='Override master seed when preparing')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--action', choices=['continue', 'retry', 'replay'], default='continue')
    parser.add_argument('--run-id')
    parser.add_argument('--index', type=int, help='Zero-based array index in the saved manifest')
    parser.add_argument('--add-replicates', type=int)
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--summary', action='store_true')
    parser.add_argument('--metric')
    args = parser.parse_args(argv)
    try:
        if args.manifest:
            batch = args.manifest.resolve().parent
        else:
            paths = args.workflow + (sorted(args.suite.glob('p53_sa_*.json')) if args.suite else [])
            if not paths:
                parser.error('Provide --workflow, --suite or --manifest')
            documents = []
            for path in paths:
                doc = read_json(path)
                settings = doc.setdefault('metadata', {}).setdefault('gui', {}).setdefault('planner', {}).setdefault('replication', {})
                if args.replicates is not None:
                    settings['replicates'] = args.replicates
                if args.master_seed is not None:
                    settings.update(masterSeed=args.master_seed, seedMode='generated')
                documents.append({'workflow': doc, 'source': str(path.resolve())})
            plan = compile_plan(documents)
            if args.preview:
                for config in plan['configurations']:
                    config.pop('workflow', None)
                print(json.dumps(plan, indent=2))
                return 0
            batch = create_batch(documents, args.runs_dir, plan)
            print(f'[PLANNER] Saved {batch / "manifest.json"}', flush=True)
            print(f'[PLANNER] {plan["unique_runs"]} unique runs ({plan["requested_runs"]} requested)', flush=True)
            print(f'[PLANNER] SLURM array range: 0-{plan["unique_runs"] - 1}', flush=True)
        if args.add_replicates is not None:
            add_replicates(batch, args.add_replicates)
        if args.status or args.summary:
            print(json.dumps(summarize_batch(batch, args.metric) if args.summary else batch_status(batch), indent=2))
            return 0
        if args.prepare:
            return 0
        return execute_batch(batch, args.action, args.run_id, args.index)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f'[PLANNER] {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    def stop(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
