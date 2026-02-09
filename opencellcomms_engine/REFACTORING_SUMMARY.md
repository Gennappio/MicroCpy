# Gene Network Workflow Functions - Transparency Refactoring

## Summary

Successfully refactored all gene network workflow functions to implement the **Transparency Principle**: all simulation logic is now visible and editable from the GUI, with no opaque method calls hiding critical algorithms.

## What Changed

### Files Refactored (7 total)

1. **initialize_hierarchical_gene_networks.py**
   - Inlined `reset()` logic (lines 116-127)
   - Inlined `get_all_states()` logic (lines 142-144)

2. **initialize_gene_networks.py**
   - Inlined `reset()` logic (lines 132-153)
   - Inlined `get_all_states()` logic (lines 159-161)

3. **propagate_and_update_gene_networks.py**
   - Inlined `HierarchicalBooleanNetwork.step()` logic (lines 111-176)
   - Inlined `_netlogo_single_gene_update()` logic (lines 125-148, 186-209)
   - Inlined `_apply_fate_hierarchy()` logic (lines 161-169)
   - Inlined `get_phenotype()` logic (lines 217-221)

4. **set_gene_network_inputs.py**
   - Inlined `set_input_states()` logic (lines 94-99)

5. **get_gene_network_states.py**
   - Inlined `get_output_states()` logic (lines 69-75)
   - Inlined `get_all_states()` logic (lines 77-81)

6. **propagate_gene_networks.py**
   - Inlined `_synchronous_step()` logic (lines 109-133)
   - Inlined `_default_step()` logic (lines 135-168)
   - Inlined `_netlogo_single_gene_update()` logic (lines 139-162)

7. **update_gene_networks_standalone.py**
   - Inlined `_synchronous_step()` logic (lines 97-121)
   - Inlined `_default_step()` logic (lines 123-156)
   - Inlined `_netlogo_single_gene_update()` logic (lines 127-150)

8. **apply_associations_to_inputs.py**
   - Inlined `set_input_states()` logic (lines 84-89)

## What's Now Visible in the GUI

When a biologist clicks "View Code" on any gene network workflow function, they now see:

### 1. **Gene Network Initialization**
- Fate nodes (Apoptosis, Proliferation, etc.) always start as `False`
- Non-input nodes start random (50/50 True/False) if `random_initialization=True`
- Input nodes keep their externally set states

### 2. **Gene Network Propagation (NetLogo Style)**
- Randomly select ONE gene per step
- Evaluate that gene's boolean expression with ALL current states
- Update ONLY that gene's state
- Repeat for N steps

### 3. **Hierarchical Fate Determination**
- Count how many times each fate gene fires during propagation
- Apply hierarchy: last fate in list that fired at least once wins
- Default hierarchy: Proliferation > Growth_Arrest > Apoptosis > Necrosis > Quiescent

### 4. **Input State Setting**
- Iterate through input nodes
- Set `node.current_state = state` for each input

### 5. **State Retrieval**
- Output states: dictionary comprehension over `output_nodes`
- All states: dictionary comprehension over all `nodes`

## Testing

Created `test_refactored_gene_networks.py` to verify:
- ✅ Initialize population
- ✅ Initialize gene networks (both regular and hierarchical)
- ✅ Set input states
- ✅ Propagate gene networks
- ✅ Retrieve gene states
- ✅ Hierarchical fate determination

**All tests pass** - the refactored code produces identical results to the original.

## What Stayed in Classes

The `BooleanNetwork` and `HierarchicalBooleanNetwork` classes still have all their methods. They work for programmatic use. The workflow functions just don't call the opaque methods anymore.

**Classes remain as data containers:**
- `BooleanNetwork.nodes: Dict[str, NetworkNode]` - stores gene nodes
- `NetworkNode.name, .current_state, .update_function, .is_input, .is_output` - node data
- `BooleanNetwork.input_nodes, .output_nodes, .fixed_nodes` - node sets
- File parsing methods (`_load_from_bnd_file`, `_parse_maboss_format`) - OK to keep hidden (I/O)

## Benefits

1. **Full Transparency**: Biologists can see exactly how gene networks update, how fates are determined, and how inputs are applied
2. **Easy Customization**: Biologists can modify the NetLogo update algorithm, change the fate hierarchy, or adjust initialization logic directly in the GUI
3. **Educational**: The code is now a teaching tool - biologists can learn how Boolean networks work by reading the workflow functions
4. **Maintainable**: All simulation logic is in one place (workflow functions), not scattered across class methods
5. **Testable**: Each workflow function can be tested independently with visible logic

## Next Steps (Not Implemented Yet)

The original plan included two more parts:

### Part 2: "Show Dependencies" Feature in GUI
- Add a "Show Dependencies" button to the code viewer
- Automatically find and display imported files
- Show which symbols were imported from each file

### Part 3: Good Practice Documentation
- Update `docs/CREATING_FUNCTIONS.md` with transparency principle
- Update `src/workflow/functions/_TEMPLATE.py` with examples
- Add checklist: "No opaque method calls hiding simulation logic"

These can be implemented in future work.

