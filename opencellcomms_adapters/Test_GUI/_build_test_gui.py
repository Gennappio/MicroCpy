"""Build Test_GUI Python files and workflow JSON.

Run once: `python _build_test_gui.py`
Produces:
- functions/<category>/*.py — one file per behavior, 3 functions inside
- workflows/test_gui.json — full ABM-format workflow
"""

import json
import os
import textwrap
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FN_DIR = HERE / 'functions'
WF_DIR = HERE / 'workflows'

# ============================================================
# Specification: maps each behavior to its functions
# ============================================================

AGENT_KINDS = {
    'predator': {
        'init': ('predator_spawn', 'predator_set_energy', 'predator_log_init'),
        'hunt': ('predator_stalk', 'predator_strike', 'predator_digest'),
        'rest': ('predator_idle', 'predator_sleep', 'predator_dream'),
        'reproduce': ('predator_court', 'predator_mate', 'predator_spawn_offspring'),
    },
    'prey': {
        'init': ('prey_spawn', 'prey_set_state', 'prey_log_init'),
        'graze': ('prey_forage', 'prey_chew', 'prey_swallow'),
        'flee': ('prey_detect_threat', 'prey_sprint', 'prey_hide'),
        'reproduce': ('prey_pair', 'prey_nest', 'prey_hatch'),
    },
    'plankton': {
        'init': ('plankton_spawn', 'plankton_set_state', 'plankton_log_init'),
        'drift': ('plankton_brownian', 'plankton_current', 'plankton_tide'),
        'photosynth': ('plankton_capture', 'plankton_convert', 'plankton_store'),
        'replicate': ('plankton_divide', 'plankton_scatter', 'plankton_settle'),
    },
}

ENV_BEHAVIORS = {
    'env_init': ('setup_test_domain', 'setup_test_substances', 'log_env_ready'),
    'env_diffuse': ('diffuse_food', 'diffuse_oxygen', 'log_diffusion'),
    'env_replenish': ('refill_food', 'refill_oxygen', 'log_replenish'),
    'env_log': ('snapshot_state', 'dump_grid', 'log_env_step'),
}

PROCESSING = {
    'proc_export_csv': ('write_predators_csv', 'write_prey_csv', 'write_plankton_csv'),
    'proc_make_plots': ('plot_populations', 'plot_environment', 'plot_interactions'),
    'proc_summary': ('print_counts', 'print_max_step', 'print_final_message'),
}


# ============================================================
# Function file generator
# ============================================================

def category_for(behavior_name):
    """Map behavior name to a registry category."""
    if behavior_name.startswith('env_'):
        return ('diffusion', 'DIFFUSION')
    if behavior_name.startswith('proc_'):
        return ('finalization', 'FINALIZATION')
    return ('intracellular', 'INTRACELLULAR')


def make_function_block(kind_scope, behavior, fn_name, category_const):
    """Generate a single @register_function block."""
    display = ' '.join(p.capitalize() for p in fn_name.split('_'))
    return textwrap.dedent(f'''
@register_function(
    display_name="{display}",
    description="[Test_GUI] {fn_name}",
    category="{category_const}",
    parameters=[
        {{"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0}},
        {{"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False}},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def {fn_name}(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {{}}).get('current_step', '?')
    print(f"[Test_GUI/{kind_scope}/{behavior}/{fn_name}] step={{step}} intensity={{intensity}}")
    if verbose:
        print(f"  -> verbose: {fn_name} fired (context keys: {{list((context or {{}}).keys())[:5]}})")
    return True
''')


def write_behavior_file(category, behavior, functions, kind_scope):
    """Write one .py file containing all functions for a behavior."""
    cat_dir, cat_const = category_for(behavior) if category == 'auto' else (category, category.upper())
    out_dir = FN_DIR / cat_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{behavior}.py'

    header = f'"""Test_GUI {behavior} — generated print-only functions."""\n\n'
    header += 'from src.workflow.decorators import register_function\n\n'

    blocks = [make_function_block(kind_scope, behavior, fn, cat_const) for fn in functions]
    out_path.write_text(header + ''.join(blocks), encoding='utf-8')
    return out_path


def write_all_function_files():
    """Generate all function files."""
    created = []

    # Agent functions go into intracellular/ for simplicity
    for kind, behaviors in AGENT_KINDS.items():
        for behavior, funcs in behaviors.items():
            path = write_behavior_file('intracellular', f'{kind}_{behavior}', funcs, kind)
            created.append(path)

    # Environment functions
    for behavior, funcs in ENV_BEHAVIORS.items():
        path = write_behavior_file('diffusion', behavior, funcs, 'environment')
        created.append(path)

    # Processing functions
    for behavior, funcs in PROCESSING.items():
        path = write_behavior_file('finalization', behavior, funcs, 'processing')
        created.append(path)

    return created


# ============================================================
# Workflow JSON generator
# ============================================================

NOW = int(time.time() * 1000)
_counter = [0]


def uid(prefix):
    _counter[0] += 1
    return f'{prefix}-{NOW}-{_counter[0]}'


def make_func_node(fn_name):
    """A single function node inside a subworkflow."""
    return {
        'id': uid('func'),
        'function_name': fn_name,
        'function_file': '',
        'parameters': {'intensity': 1.0, 'verbose': False},
        'enabled': True,
        'position': {'x': 400, 'y': 100 + _counter[0] * 60 % 600},
        'description': '',
        'custom_name': '',
        'step_count': 1,
        'parameter_nodes': [],
    }


def make_subwf(name, description, deletable, fn_names):
    """A subworkflow with controller + sequential function nodes wired in execution order."""
    controller = {
        'id': f'controller-{name}',
        'type': 'controller',
        'label': f'{name.upper()} CONTROLLER',
        'position': {'x': 100, 'y': 100},
        'number_of_steps': 1,
    }
    funcs = [make_func_node(fn) for fn in fn_names]
    execution_order = [f['id'] for f in funcs]
    return {
        'description': description,
        'enabled': True,
        'deletable': deletable,
        'controller': controller,
        'functions': funcs,
        'subworkflow_calls': [],
        'parameters': [],
        'execution_order': execution_order,
        'input_parameters': [],
    }


def make_scheduler_subwf(behaviors):
    """The scheduler subworkflow — only contains subworkflow_call nodes."""
    controller = {
        'id': 'controller-__scheduler__',
        'type': 'controller',
        'label': 'SCHEDULER',
        'position': {'x': 100, 'y': 100},
        'number_of_steps': 10,
    }
    calls = []
    for i, behavior_name in enumerate(behaviors):
        call_id = uid('sched-call')
        calls.append({
            'id': call_id,
            'type': 'subworkflow_call',
            'subworkflow_name': behavior_name,
            'iterations': 1,
            'parameters': {},
            'enabled': True,
            'position': {'x': 400, 'y': 120 + i * 110},
            'description': behavior_name,
            'parameter_nodes': [],
        })
    execution_order = [c['id'] for c in calls]
    return {
        'description': 'Test_GUI scheduler (main loop)',
        'enabled': True,
        'deletable': False,
        'controller': controller,
        'functions': [],
        'subworkflow_calls': calls,
        'parameters': [],
        'execution_order': execution_order,
        'input_parameters': [],
    }


def make_main_subwf(env_init_name, agent_inits, scheduler_steps, processing_behaviors):
    """The synthesized 'main' composer — env init → agent inits → loop scheduler N times → processing."""
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

    if env_init_name:
        add(env_init_name, 1, 'Environment init')
    for init in agent_inits:
        add(init, 1, 'Agent init')
    add('__scheduler__', scheduler_steps, 'Main loop')
    for proc in processing_behaviors:
        add(proc, 1, 'Processing')

    return {
        'description': 'Synthesized main (do not edit — managed by ABM structure)',
        'enabled': True,
        'deletable': False,
        'controller': controller,
        'functions': [],
        'subworkflow_calls': calls,
        'parameters': [],
        'execution_order': [c['id'] for c in calls],
        'input_parameters': [],
    }


def build_workflow():
    subworkflows = {}
    kinds = {}

    # Agent inits + behaviors
    agent_kinds_meta = []
    for kind, behaviors in AGENT_KINDS.items():
        init_name = f'{kind}_init'
        # The init "behavior" name in our spec is 'init' — but the subworkflow is named with the suffix
        init_funcs = behaviors['init']
        subworkflows[init_name] = make_subwf(init_name, f'{kind} initialization', True, list(init_funcs))
        kinds[init_name] = 'agent_init'

        behavior_subwfs = []
        for bname, funcs in behaviors.items():
            if bname == 'init':
                continue
            sw_name = f'{kind}_{bname}'
            subworkflows[sw_name] = make_subwf(sw_name, f'{kind} behavior: {bname}', True, list(funcs))
            kinds[sw_name] = 'agent_behavior'
            behavior_subwfs.append(sw_name)

        agent_kinds_meta.append({
            'name': kind,
            'init_subworkflow': init_name,
            'behavior_subworkflows': behavior_subwfs,
        })

    # Environment
    env_init_funcs = ENV_BEHAVIORS['env_init']
    subworkflows['env_init'] = make_subwf('env_init', 'Environment initialization', True, list(env_init_funcs))
    kinds['env_init'] = 'env_init'

    env_behavior_names = []
    for bname, funcs in ENV_BEHAVIORS.items():
        if bname == 'env_init':
            continue
        subworkflows[bname] = make_subwf(bname, f'Environment behavior: {bname}', True, list(funcs))
        kinds[bname] = 'env_behavior'
        env_behavior_names.append(bname)

    # Processing
    processing_names = []
    for bname, funcs in PROCESSING.items():
        subworkflows[bname] = make_subwf(bname, f'Processing: {bname}', True, list(funcs))
        kinds[bname] = 'processing_behavior'
        processing_names.append(bname)

    # Scheduler (mixed-order interleaving of env + agent behaviors)
    scheduler_order = [
        'env_diffuse',
        'predator_hunt',
        'prey_flee',
        'plankton_drift',
        'env_replenish',
        'predator_rest',
        'prey_graze',
        'plankton_photosynth',
        'env_log',
        'predator_reproduce',
        'prey_reproduce',
        'plankton_replicate',
    ]
    subworkflows['__scheduler__'] = make_scheduler_subwf(scheduler_order)
    kinds['__scheduler__'] = 'scheduler'

    # Synthesized main
    agent_init_names = [k['init_subworkflow'] for k in agent_kinds_meta]
    main_steps = subworkflows['__scheduler__']['controller']['number_of_steps']
    subworkflows['main'] = make_main_subwf('env_init', agent_init_names, main_steps, processing_names)
    kinds['main'] = 'composer'

    # Planner tabs
    planner_tabs = [
        {'id': 'tab-baseline', 'name': 'run_baseline', 'enabled': True, 'parameterOverrides': {}},
        {'id': 'tab-pressure', 'name': 'run_high_predator_pressure', 'enabled': True,
         'parameterOverrides': {'predator_hunt': {'intensity': 5.0}}},
        {'id': 'tab-lowfood', 'name': 'run_low_food', 'enabled': True,
         'parameterOverrides': {'env_replenish': {'intensity': 0.2}}},
        {'id': 'tab-long', 'name': 'run_long', 'enabled': True,
         'parameterOverrides': {'__scheduler__': {'number_of_steps': 30}}},
        {'id': 'tab-silent', 'name': 'run_silent', 'enabled': False, 'parameterOverrides': {}},
    ]

    workflow = {
        'version': '2.0',
        'name': 'Test_GUI',
        'description': 'Stress-test workflow: 3 agent kinds, mixed scheduler, planner runs, processing.',
        'metadata': {
            'author': 'Test_GUI generator',
            'created': time.strftime('%Y-%m-%d'),
            'gui': {
                'subworkflow_kinds': kinds,
                'function_libraries': [],
                'agent_kinds': agent_kinds_meta,
                'environment': {
                    'init_subworkflow': 'env_init',
                    'behavior_subworkflows': env_behavior_names,
                },
                'scheduler': {'subworkflow': '__scheduler__'},
                'processing': {'behavior_subworkflows': processing_names},
                'main_is_synthesized': True,
                'user_functions': [],
                'planner': {'tabs': planner_tabs},
            },
        },
        'subworkflows': subworkflows,
    }
    return workflow


def write_workflow():
    WF_DIR.mkdir(parents=True, exist_ok=True)
    out = WF_DIR / 'test_gui.json'
    wf = build_workflow()
    out.write_text(json.dumps(wf, indent=2), encoding='utf-8')
    return out


# ============================================================
# Register.py generator
# ============================================================

def write_register_py():
    lines = ['"""Auto-generated: import every Test_GUI function module to trigger registration."""', '']
    for kind, behaviors in AGENT_KINDS.items():
        for behavior in behaviors:
            module = f'{kind}_{behavior}'
            lines.append(f'import opencellcomms_adapters.Test_GUI.functions.intracellular.{module}  # noqa: F401')
    for bname in ENV_BEHAVIORS:
        lines.append(f'import opencellcomms_adapters.Test_GUI.functions.diffusion.{bname}  # noqa: F401')
    for bname in PROCESSING:
        lines.append(f'import opencellcomms_adapters.Test_GUI.functions.finalization.{bname}  # noqa: F401')
    (HERE / 'register.py').write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ============================================================
# Init files
# ============================================================

def write_init_files():
    for d in [HERE, FN_DIR, FN_DIR / 'intracellular', FN_DIR / 'diffusion', FN_DIR / 'finalization']:
        d.mkdir(parents=True, exist_ok=True)
        (d / '__init__.py').write_text('', encoding='utf-8')


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    write_init_files()
    created = write_all_function_files()
    write_register_py()
    out = write_workflow()
    print(f'Wrote {len(created)} function files')
    for p in created:
        print(f'  {p.relative_to(HERE)}')
    print(f'Wrote register.py')
    print(f'Wrote workflow: {out.relative_to(HERE)}')
