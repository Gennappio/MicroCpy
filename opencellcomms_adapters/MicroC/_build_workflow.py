"""Convert the v7 jayatilake workflow to the new ABM-format MicroC workflow.

Reads:  opencellcomms_adapters/jayatilake/workflows/v7_microc_workflow.json
Writes: opencellcomms_adapters/MicroC/workflows/microc.json

Preserves all enabled function parameters from the v7 source (parity).
"""

import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
V7 = REPO / 'opencellcomms_adapters' / 'jayatilake' / 'workflows' / 'v7_microc_workflow.json'
OUT = HERE / 'workflows' / 'microc.json'

# Map: target ABM subworkflow → (source v7 subworkflow, function names to include, source for parameter_nodes)
# function names listed below are the ENABLED functions we want to keep.
MAPPING = [
    # (target_name, target_kind, source_subworkflow, [function_names_to_include])
    ('environment_init',   'env_init',            None,                ['__merge_env_init__']),
    ('tumor_cell_init',    'agent_init',          None,                ['__merge_agent_init__']),
    ('diffusion_step',     'env_behavior',        'microenvironment',  ['run_diffusion_solver_coupled']),
    ('iteration_plots',    'env_behavior',        'Generate_loop_plots', ['generate_iteration_plots']),
    ('gene_update',        'agent_behavior',      'intracellular',     ['apply_associations_to_inputs', 'propagate_gene_networks_netlogo']),
    ('fate_update',        'agent_behavior',      'intercellular',     ['mark_necrotic_cells', 'mark_growth_arrest_cells', 'mark_apoptotic_cells', 'mark_proliferating_cells']),
    ('division',           'agent_behavior',      'intercellular',     ['update_cell_division', 'remove_apoptotic_cells']),
    ('final_summary',      'processing_behavior', 'Generate_final_plots', ['generate_summary_plots']),
]

# Subworkflows that are MERGED from multiple v7 sources
ENV_INIT_SOURCES = [
    ('Setup_simulation', ['setup_simulation', 'setup_domain']),
    ('Setup_substances', ['setup_substances']),
    ('Setup_associations', ['setup_associations']),
]
AGENT_INIT_SOURCES = [
    ('Setup_population', ['setup_population', 'read_checkpoint']),
    ('Init_gene_networks', ['initialize_netlogo_gene_networks']),
]

# Path-rewrite: change references from "../data/..." (jayatilake-relative) to "../data/..." (MicroC-relative).
# Since the MicroC adapter copies the data files, the relative paths stay valid as-is.
PATH_REWRITES = {}


def find_fn(sw, fn_name):
    """Find a function node in a v7 subworkflow by name."""
    for f in sw.get('functions', []):
        if f.get('function_name') == fn_name:
            return f
    return None


def collect_param_nodes(sw, fn_node):
    """Return the parameter node objects referenced by `fn_node.parameter_nodes`."""
    pids = set(fn_node.get('parameter_nodes', []))
    return [p for p in sw.get('parameters', []) if p.get('id') in pids]


def remap_id(orig_id, prefix):
    """Generate a stable new ID preserving uniqueness."""
    return f'{prefix}-{orig_id}'


def build_subworkflow(target_name, source_sw, fn_names, prefix):
    """Build a new ABM-format subworkflow from one or more v7 source subworkflows."""
    fns = []
    params = []
    seen_param_ids = set()
    x_base, y = 400, 100

    for fn_name in fn_names:
        fn_node = find_fn(source_sw, fn_name)
        if not fn_node:
            print(f'[WARN] {target_name}: function {fn_name!r} not found in source {source_sw.get("name","?")}')
            continue
        # Remap function ID with prefix to keep them unique across the new workflow
        new_fn_id = remap_id(fn_node['id'], prefix)
        new_fn = {
            'id': new_fn_id,
            'function_name': fn_node['function_name'],
            'function_file': fn_node.get('function_file', ''),
            'parameters': dict(fn_node.get('parameters', {})),
            'enabled': True,  # force-enable on copy
            'position': {'x': x_base, 'y': y},
            'description': fn_node.get('description', ''),
            'custom_name': fn_node.get('custom_name', ''),
            'step_count': fn_node.get('step_count', 1),
            'parameter_nodes': [],
        }
        y += 100

        # Copy attached parameter nodes (remap IDs too)
        for pnode in collect_param_nodes(source_sw, fn_node):
            new_pid = remap_id(pnode['id'], prefix)
            if new_pid in seen_param_ids:
                continue
            seen_param_ids.add(new_pid)
            new_pnode = dict(pnode)
            new_pnode['id'] = new_pid
            new_pnode['position'] = {'x': 100, 'y': y + 200}
            params.append(new_pnode)
            new_fn['parameter_nodes'].append(new_pid)

        fns.append(new_fn)

    controller = {
        'id': f'controller-{target_name}',
        'type': 'controller',
        'label': f'{target_name.upper()} CONTROLLER',
        'position': {'x': 100, 'y': 100},
        'number_of_steps': 1,
    }
    return {
        'description': f'MicroC: {target_name}',
        'enabled': True,
        'deletable': True,
        'controller': controller,
        'functions': fns,
        'subworkflow_calls': [],
        'parameters': params,
        'execution_order': [f['id'] for f in fns],
        'input_parameters': [],
    }


def build_merged_subworkflow(target_name, v7, source_list, prefix):
    """Build a subworkflow that merges functions from multiple v7 subworkflows."""
    fns = []
    params = []
    seen_param_ids = set()
    x_base, y = 400, 100

    for src_name, fn_names in source_list:
        sw = v7['subworkflows'].get(src_name)
        if not sw:
            print(f'[WARN] {target_name}: source {src_name!r} not found')
            continue
        for fn_name in fn_names:
            fn_node = find_fn(sw, fn_name)
            if not fn_node:
                print(f'[WARN] {target_name}: function {fn_name!r} not found in {src_name}')
                continue
            new_fn_id = remap_id(fn_node['id'], f'{prefix}-{src_name}')
            new_fn = {
                'id': new_fn_id,
                'function_name': fn_node['function_name'],
                'function_file': fn_node.get('function_file', ''),
                'parameters': dict(fn_node.get('parameters', {})),
                'enabled': True,
                'position': {'x': x_base, 'y': y},
                'description': fn_node.get('description', ''),
                'custom_name': fn_node.get('custom_name', ''),
                'step_count': fn_node.get('step_count', 1),
                'parameter_nodes': [],
            }
            y += 100

            for pnode in collect_param_nodes(sw, fn_node):
                new_pid = remap_id(pnode['id'], f'{prefix}-{src_name}')
                if new_pid in seen_param_ids:
                    continue
                seen_param_ids.add(new_pid)
                new_pnode = dict(pnode)
                new_pnode['id'] = new_pid
                new_pnode['position'] = {'x': 100, 'y': y + 200}
                params.append(new_pnode)
                new_fn['parameter_nodes'].append(new_pid)

            fns.append(new_fn)

    controller = {
        'id': f'controller-{target_name}',
        'type': 'controller',
        'label': f'{target_name.upper()} CONTROLLER',
        'position': {'x': 100, 'y': 100},
        'number_of_steps': 1,
    }
    return {
        'description': f'MicroC: {target_name} (merged from v7 {", ".join(s[0] for s in source_list)})',
        'enabled': True,
        'deletable': True,
        'controller': controller,
        'functions': fns,
        'subworkflow_calls': [],
        'parameters': params,
        'execution_order': [f['id'] for f in fns],
        'input_parameters': [],
    }


def make_scheduler(order, steps):
    controller = {
        'id': 'controller-__scheduler__',
        'type': 'controller',
        'label': 'SCHEDULER',
        'position': {'x': 100, 'y': 100},
        'number_of_steps': steps,
    }
    calls = []
    for i, name in enumerate(order):
        cid = f'sched-call-{name}'
        calls.append({
            'id': cid,
            'type': 'subworkflow_call',
            'subworkflow_name': name,
            'iterations': 1,
            'parameters': {},
            'enabled': True,
            'position': {'x': 400, 'y': 120 + i * 110},
            'description': name,
            'parameter_nodes': [],
        })
    return {
        'description': 'MicroC main simulation loop',
        'enabled': True,
        'deletable': False,
        'controller': controller,
        'functions': [],
        'subworkflow_calls': calls,
        'parameters': [],
        'execution_order': [c['id'] for c in calls],
        'input_parameters': [],
    }


def make_main(env_init, agent_inits, sched_steps, processing):
    controller = {
        'id': 'controller-main',
        'type': 'controller',
        'label': 'MAIN CONTROLLER',
        'position': {'x': 100, 'y': 100},
        'number_of_steps': 1,
    }
    calls = []
    y = 200
    def add(name, iters, desc):
        nonlocal y
        cid = f'main-call-{name}'
        calls.append({
            'id': cid,
            'type': 'subworkflow_call',
            'subworkflow_name': name,
            'iterations': iters,
            'parameters': {},
            'enabled': True,
            'position': {'x': 400, 'y': y},
            'description': desc,
            'parameter_nodes': [],
        })
        y += 120

    if env_init:
        add(env_init, 1, 'Environment init')
    for init in agent_inits:
        add(init, 1, 'Agent init')
    add('__scheduler__', sched_steps, 'Main loop')
    for proc in processing:
        add(proc, 1, 'Processing')

    return {
        'description': 'Synthesized main composer for MicroC (do not edit)',
        'enabled': True,
        'deletable': False,
        'controller': controller,
        'functions': [],
        'subworkflow_calls': calls,
        'parameters': [],
        'execution_order': [c['id'] for c in calls],
        'input_parameters': [],
    }


def main():
    v7 = json.loads(V7.read_text(encoding='utf-8'))
    subworkflows = {}
    kinds = {}

    # Build the merged init subworkflows
    subworkflows['environment_init'] = build_merged_subworkflow('environment_init', v7, ENV_INIT_SOURCES, 'envinit')
    kinds['environment_init'] = 'env_init'

    subworkflows['tumor_cell_init'] = build_merged_subworkflow('tumor_cell_init', v7, AGENT_INIT_SOURCES, 'agentinit')
    kinds['tumor_cell_init'] = 'agent_init'

    # Build per-source behaviors
    for target, kind, source, fn_names in MAPPING:
        if source is None:
            continue  # already built above (merged)
        sw = v7['subworkflows'].get(source)
        if not sw:
            print(f'[WARN] source {source!r} missing for {target}')
            continue
        subworkflows[target] = build_subworkflow(target, sw, fn_names, target)
        kinds[target] = kind

    # Scheduler
    scheduler_order = ['diffusion_step', 'gene_update', 'fate_update', 'division', 'iteration_plots']
    subworkflows['__scheduler__'] = make_scheduler(scheduler_order, 30)
    kinds['__scheduler__'] = 'scheduler'

    # Main composer (synthesized)
    subworkflows['main'] = make_main(
        env_init='environment_init',
        agent_inits=['tumor_cell_init'],
        sched_steps=30,
        processing=['final_summary'],
    )
    kinds['main'] = 'composer'

    # Assemble metadata
    workflow = {
        'version': '2.0',
        'name': 'MicroC',
        'description': '1:1 re-expression of the jayatilake v7 model in the new ABM workflow format.',
        'metadata': {
            'author': 'MicroC builder',
            'created': time.strftime('%Y-%m-%d'),
            'gui': {
                'subworkflow_kinds': kinds,
                'function_libraries': [],
                'agent_kinds': [{
                    'name': 'tumor_cell',
                    'init_subworkflow': 'tumor_cell_init',
                    'behavior_subworkflows': ['gene_update', 'fate_update', 'division'],
                }],
                'environment': {
                    'init_subworkflow': 'environment_init',
                    'behavior_subworkflows': ['diffusion_step', 'iteration_plots'],
                },
                'scheduler': {'subworkflow': '__scheduler__'},
                'processing': {'behavior_subworkflows': ['final_summary']},
                'main_is_synthesized': True,
                'user_functions': [],
            },
        },
        'subworkflows': subworkflows,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(workflow, indent=2), encoding='utf-8')
    print(f'Wrote {OUT.relative_to(REPO)}')
    print(f'  subworkflows: {len(subworkflows)}')
    print(f'  agent_kinds: 1 (tumor_cell)')
    print(f'  env_behaviors: 2')
    print(f'  scheduler steps: {len(scheduler_order)} × 30 iterations')
    print(f'  processing behaviors: 1')


if __name__ == '__main__':
    main()
