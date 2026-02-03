#!/usr/bin/env python3
"""
Analyze when one output node is more probable than another.

Given a JSON from `gene_network_confusion.py`, compute for each input combination:
  delta = P(A) - P(B)

Outputs:
  - counts of delta>0, delta=0, delta<0
  - best/worst combinations by delta
  - top-K combinations by delta (closest to A beating B)
  - which inputs are most determinant for delta (mean delta when input ON vs OFF)

Example:
  python pairwise_delta_analysis.py results_apoptosis.json --a Proliferation --b Apoptosis
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def _get_prob(combo_data: Dict[str, Any], node: str) -> float:
    probs = combo_data.get("output_probabilities", {})
    if node not in probs:
        raise KeyError(
            f"Node '{node}' not found in output_probabilities. "
            f"Available: {sorted(list(probs.keys()))}"
        )
    return float(probs[node])


def _format_on_off(input_states: Dict[str, bool]) -> str:
    on = [k for k, v in input_states.items() if v]
    off = [k for k, v in input_states.items() if not v]
    return (
        f"ON: {', '.join(sorted(on)) if on else '(none)'} | "
        f"OFF: {', '.join(sorted(off)) if off else '(none)'}"
    )


@dataclass(frozen=True)
class DeltaEffect:
    input_node: str
    mean_on: float
    mean_off: float

    @property
    def diff(self) -> float:
        return self.mean_on - self.mean_off

    @property
    def abs_diff(self) -> float:
        return abs(self.diff)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pairwise delta analysis P(A) - P(B).")
    parser.add_argument("json_file", help="JSON produced by gene_network_confusion.py")
    parser.add_argument("--a", required=True, help="Node A in delta = P(A) - P(B)")
    parser.add_argument("--b", required=True, help="Node B in delta = P(A) - P(B)")
    parser.add_argument("--top", type=int, default=15, help="Show top-K combinations by delta (default: 15)")
    args = parser.parse_args()

    data = _load_json(args.json_file)
    input_nodes: List[str] = data["input_nodes"]
    all_results: Dict[str, Any] = data["all_results"]

    rows: List[Tuple[float, float, float, Dict[str, bool]]] = []
    for combo in all_results.values():
        pa = _get_prob(combo, args.a)
        pb = _get_prob(combo, args.b)
        rows.append((pa - pb, pa, pb, combo["input_states"]))

    n = len(rows)
    pos = sum(1 for d, *_ in rows if d > 0)
    neg = sum(1 for d, *_ in rows if d < 0)
    eq = n - pos - neg

    rows_sorted = sorted(rows, key=lambda x: x[0], reverse=True)
    best = rows_sorted[0]
    worst = rows_sorted[-1]

    print(f"File: {args.json_file}")
    print(f"Output nodes: {data.get('output_nodes')}")
    print(f"Combinations: {n}")
    print(f"Delta = P({args.a}) - P({args.b})")
    print(f"  Delta>0: {pos}")
    print(f"  Delta=0: {eq}")
    print(f"  Delta<0: {neg}")
    print()

    d, pa, pb, ins = best
    print("Best (highest Delta) combination:")
    print(f"  {args.a}={pa*100:.1f}%  {args.b}={pb*100:.1f}%  Delta={d*100:+.1f} pp")
    print(f"  {_format_on_off(ins)}")
    print()

    d, pa, pb, ins = worst
    print("Worst (lowest Delta) combination:")
    print(f"  {args.a}={pa*100:.1f}%  {args.b}={pb*100:.1f}%  Delta={d*100:+.1f} pp")
    print(f"  {_format_on_off(ins)}")

    # input determinants for delta
    buckets: Dict[str, Dict[str, List[float]]] = {
        n0: {"on": [], "off": []} for n0 in input_nodes
    }
    for d, pa, pb, ins in rows:
        for n0 in input_nodes:
            buckets[n0]["on" if ins[n0] else "off"].append(d)

    effects: List[DeltaEffect] = []
    for n0 in input_nodes:
        on = buckets[n0]["on"]
        off = buckets[n0]["off"]
        mean_on = sum(on) / len(on) if on else 0.0
        mean_off = sum(off) / len(off) if off else 0.0
        effects.append(DeltaEffect(input_node=n0, mean_on=mean_on, mean_off=mean_off))

    effects.sort(key=lambda e: e.abs_diff, reverse=True)
    print()
    print("Ranked input determinants for Delta (mean Delta pp when ON vs OFF):")
    print("abs_diff_pp\tdiff_pp\tmean_on\tmean_off\tinput")
    for e in effects:
        print(
            f"{e.abs_diff*100:6.2f}\t{e.diff*100:+6.2f}\t{e.mean_on*100:+6.2f}\t{e.mean_off*100:+6.2f}\t{e.input_node}"
        )

    if args.top > 0:
        print()
        print(f"Top {args.top} combinations by Delta (closest to {args.a} beating {args.b}):")
        for i, (d, pa, pb, ins) in enumerate(rows_sorted[: args.top], 1):
            on = [k for k, v in ins.items() if v]
            print(
                f"#{i:02d} Delta={d*100:+.1f}pp | {args.a}={pa*100:.1f}% {args.b}={pb*100:.1f}% | "
                f"ON: {', '.join(sorted(on)) if on else '(none)'}"
            )


if __name__ == "__main__":
    main()

