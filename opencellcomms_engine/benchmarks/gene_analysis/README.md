## Gene analysis helpers (from confusion-matrix JSON)

This folder contains the small analysis scripts used in chat to answer:

- Which input nodes are most determinant for a given output (e.g. `Proliferation`, `Apoptosis`)
- In which cases one output is more probable than another (e.g. `Proliferation` vs `Apoptosis`)

All scripts expect the JSON format produced by `opencellcomms_engine/benchmarks/gene_network_confusion.py`.

### 1) Determinant inputs for an output node

Ranks inputs by the change in mean activation probability when the input is ON vs OFF:

```bash
python opencellcomms_engine/benchmarks/gene_analysis/determinant_inputs.py \
  results.json \
  --node Proliferation
```

For the Apoptosis run:

```bash
python opencellcomms_engine/benchmarks/gene_analysis/determinant_inputs.py \
  results_apoptosis.json \
  --node Apoptosis
```

### 2) “When is A more probable than B?”

Computes \(\Delta = P(A) - P(B)\) for every input combination; reports how many combos have \(\Delta>0\),
and shows the top combinations by \(\Delta\). Also ranks which inputs move \(\Delta\) most when toggled.

```bash
python opencellcomms_engine/benchmarks/gene_analysis/pairwise_delta_analysis.py \
  results_apoptosis.json \
  --a Proliferation \
  --b Apoptosis
```

