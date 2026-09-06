#!/usr/bin/env python3
"""Run the Planner definition stored in one or more workflow JSON files."""
import argparse
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.workflow.replication import (REPO, compile_plan, create_batch,
    execute_batch, read_json)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow', type=Path, action='append', default=[])
    parser.add_argument('--suite', type=Path,
                        help='Run all p53_sa_*.json workflows together (deduplicates baselines)')
    parser.add_argument('--runs-dir', type=Path, default=REPO / 'runs')
    # The GUI uses these hidden options to continue an already-created result
    # folder. Scientists define and change plans only in workflow JSON files.
    parser.add_argument('--manifest', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--action', choices=['continue', 'retry', 'replay'],
                        default='continue', help=argparse.SUPPRESS)
    parser.add_argument('--run-id', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.manifest:
            batch = args.manifest.resolve().parent
        else:
            paths = args.workflow + (sorted(args.suite.glob('p53_sa_*.json')) if args.suite else [])
            if not paths:
                parser.error('Provide --workflow or --suite')
            documents = []
            for path in paths:
                doc = read_json(path)
                documents.append({'workflow': doc, 'source': str(path.resolve())})
            plan = compile_plan(documents)
            batch = create_batch(documents, args.runs_dir, plan)
            print(f'[PLANNER] Results folder: {batch}', flush=True)
            print(f'[PLANNER] {plan["unique_runs"]} unique runs ({plan["requested_runs"]} requested)', flush=True)
        return execute_batch(batch, args.action, args.run_id)
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
