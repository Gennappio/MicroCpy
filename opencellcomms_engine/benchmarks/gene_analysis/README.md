## Gene analysis helpers (from confusion-matrix JSON)

This folder contains the small analysis scripts used in chat to answer:

- Which input nodes are most determinant for a given output (e.g. `Proliferation`, `Apoptosis`)
- In which cases one output is more probable than another (e.g. `Proliferation` vs `Apoptosis`)
- Phenotype distribution when applying a hierarchy rule (e.g. `Proliferation > Growth_Arrest > Apoptosis`)

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

### 3) Phenotype hierarchy analysis

When multiple fate nodes are simultaneously ON in a simulation, the higher-priority one determines 
the final phenotype. For example, if both `Proliferation=ON` and `Apoptosis=ON`, the phenotype is 
"Proliferation" (Proliferation wins over Apoptosis).

Default hierarchy: **Proliferation > Growth_Arrest > Apoptosis**

Using an independence assumption, effective phenotype probabilities are computed as:
- `P(Phenotype=Proliferation) = P(Prolif ON)`
- `P(Phenotype=Growth_Arrest) = P(GA ON) * (1 - P(Prolif ON))`
- `P(Phenotype=Apoptosis) = P(Apop ON) * (1 - P(GA ON)) * (1 - P(Prolif ON))`
- `P(Quiescent) = (1 - P(Prolif)) * (1 - P(GA)) * (1 - P(Apop))`

```bash
python opencellcomms_engine/benchmarks/gene_analysis/phenotype_hierarchy_analysis.py \
  results_apoptosis.json

# Show top 20 combinations and save to file
python opencellcomms_engine/benchmarks/gene_analysis/phenotype_hierarchy_analysis.py \
  results_apoptosis.json \
  --top 20 \
  --output hierarchy_report.txt
```

