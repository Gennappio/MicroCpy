#!/usr/bin/env python3
"""
Rank which input nodes are most determinant for a chosen output node.

Input:
  A JSON produced by `gene_network_confusion.py` with fields:
    - input_nodes: [str]
    - all_results: { combo_idx: { input_states: {str: bool}, output_probabilities: {str: float} } }

Method:
  For each input node X, compute:
    mean(P(target) | X=ON) and mean(P(target) | X=OFF)
  Then rank by |mean_on - mean_off|.

Example:
  python determinant_inputs.py results.json --node Proliferation
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class InputEffect:
    input_node: str
    mean_on: float
    mean_off: float

    @property
    def diff(self) -> float:
        return self.mean_on - self.mean_off

    @property
    def abs_diff(self) -> float:
        return abs(self.diff)


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


def compute_input_effects(
    data: Dict[str, Any], target_node: str
) -> Tuple[float, List[InputEffect]]:
    input_nodes: List[str] = data["input_nodes"]
    all_results: Dict[str, Any] = data["all_results"]

    # Collect probabilities for overall mean
    all_probs: List[float] = []

    # For each input node, collect probs when ON and OFF
    buckets: Dict[str, Dict[str, List[float]]] = {
        n: {"on": [], "off": []} for n in input_nodes
    }

    for combo in all_results.values():
        p = _get_prob(combo, target_node)
        all_probs.append(p)
        input_states: Dict[str, bool] = combo["input_states"]
        for n in input_nodes:
            buckets[n]["on" if input_states[n] else "off"].append(p)

    overall_mean = sum(all_probs) / len(all_probs) if all_probs else 0.0

    effects: List[InputEffect] = []
    for n in input_nodes:
        on = buckets[n]["on"]
        off = buckets[n]["off"]
        mean_on = sum(on) / len(on) if on else 0.0
        mean_off = sum(off) / len(off) if off else 0.0
        effects.append(InputEffect(input_node=n, mean_on=mean_on, mean_off=mean_off))

    effects.sort(key=lambda e: e.abs_diff, reverse=True)
    return overall_mean, effects


def top_combinations(
    data: Dict[str, Any], target_node: str, k: int
) -> List[Tuple[float, Dict[str, bool]]]:
    all_results: Dict[str, Any] = data["all_results"]
    combos: List[Tuple[float, Dict[str, bool]]] = []
    for combo in all_results.values():
        p = _get_prob(combo, target_node)
        combos.append((p, combo["input_states"]))
    combos.sort(key=lambda x: x[0], reverse=True)
    return combos[:k]


def _format_on_off(input_states: Dict[str, bool]) -> str:
    on = [k for k, v in input_states.items() if v]
    off = [k for k, v in input_states.items() if not v]
    return (
        f"ON: {', '.join(sorted(on)) if on else '(none)'} | "
        f"OFF: {', '.join(sorted(off)) if off else '(none)'}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rank determinant input nodes for a target output node."
    )
    parser.add_argument("json_file", help="JSON produced by gene_network_confusion.py")
    parser.add_argument("--node", required=True, help="Target output node, e.g. Proliferation")
    parser.add_argument("--top", type=int, default=15, help="Show top-k input combinations (default: 15)")
    args = parser.parse_args()

    data = _load_json(args.json_file)

    overall_mean, effects = compute_input_effects(data, args.node)
    print(f"File: {args.json_file}")
    print(f"Output nodes: {data.get('output_nodes')}")
    print(f"Overall mean {args.node} probability across combos: {overall_mean*100:.2f}%")
    print()
    print(f"Ranked input determinants for {args.node} (mean {args.node}% when ON vs OFF):")
    print("abs_diff_pp\tdiff_pp\tmean_on\tmean_off\tinput")
    for e in effects:
        print(
            f"{e.abs_diff*100:6.2f}\t{e.diff*100:+6.2f}\t{e.mean_on*100:6.2f}\t{e.mean_off*100:6.2f}\t{e.input_node}"
        )

    if args.top > 0:
        print()
        print(f"Top {args.top} input combinations by {args.node} probability:")
        for i, (p, ins) in enumerate(top_combinations(data, args.node, args.top), 1):
            print(f"#{i:02d} {args.node}={p*100:.1f}% | {_format_on_off(ins)}")


if __name__ == "__main__":
    main()

