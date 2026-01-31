#!/usr/bin/env python
"""Quick performance test for gene network."""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from src.biology.gene_network import BooleanNetwork
from src.biology.cell import Cell
from pathlib import Path
import time

def main():
    # Load directly from BND file
    print('Loading BND file...')
    start = time.time()
    gn = BooleanNetwork(network_file=Path('tests/jayatilake_experiment/jaya_microc.bnd'))
    print(f'Loaded in {time.time()-start:.3f}s')

    print(f'Input nodes: {len(gn.input_nodes)}')
    print(f'Total nodes: {len(gn.nodes)}')

    # Test copy performance
    print('\nTesting copy performance (1000 copies)...')
    start = time.time()
    copies = [gn.copy() for _ in range(1000)]
    elapsed = time.time()-start
    print(f'1000 copies in {elapsed:.3f}s')

    # Test step performance
    print('\nTesting step performance (1000 cells x 20 steps)...')
    start = time.time()
    for i, network in enumerate(copies):
        network.set_input_states({
            'Oxygen_supply': True,
            'Glucose_supply': True,
            'MCT1_stimulus': True,
        })
        states = network.step(20, mode='synchronous')
    elapsed = time.time()-start
    print(f'1000 cells x 20 steps in {elapsed:.3f}s')

    # Check final states
    mito = states.get("mitoATP")
    glyco = states.get("glycoATP")
    print(f'\nFinal states sample:')
    print(f'  mitoATP: {mito}')
    print(f'  glycoATP: {glyco}')

    # Test different conditions
    print('\n--- Testing different conditions ---')

    # Test with oxygen + glucose
    gn1 = BooleanNetwork(network_file=Path('tests/jayatilake_experiment/jaya_microc.bnd'))
    gn1.set_input_states({'Oxygen_supply': True, 'Glucose_supply': True})
    s1 = gn1.step(20, mode='synchronous')
    print(f'Oxygen+Glucose: mitoATP={s1.get("mitoATP")}, glycoATP={s1.get("glycoATP")}')

    # Test with oxygen only
    gn2 = BooleanNetwork(network_file=Path('tests/jayatilake_experiment/jaya_microc.bnd'))
    gn2.set_input_states({'Oxygen_supply': True, 'Glucose_supply': False})
    s2 = gn2.step(20, mode='synchronous')
    print(f'Oxygen only:    mitoATP={s2.get("mitoATP")}, glycoATP={s2.get("glycoATP")}')

    # Test with glucose only (hypoxia)
    gn3 = BooleanNetwork(network_file=Path('tests/jayatilake_experiment/jaya_microc.bnd'))
    gn3.set_input_states({'Oxygen_supply': False, 'Glucose_supply': True, 'MCT1_stimulus': True})
    s3 = gn3.step(20, mode='synchronous')
    print(f'Glucose only:   mitoATP={s3.get("mitoATP")}, glycoATP={s3.get("glycoATP")}')

    # Test with nothing
    gn4 = BooleanNetwork(network_file=Path('tests/jayatilake_experiment/jaya_microc.bnd'))
    gn4.set_input_states({'Oxygen_supply': False, 'Glucose_supply': False})
    s4 = gn4.step(20, mode='synchronous')
    print(f'Nothing:        mitoATP={s4.get("mitoATP")}, glycoATP={s4.get("glycoATP")}')

    # Test cell integration
    print('\n--- Testing Cell Integration ---')
    cell = Cell(position=(100, 100), phenotype="Growth_Arrest", cell_id="test_cell")
    print(f'Initial gene_states: {cell.state.gene_states}')

    # Attach gene network
    cell.state = cell.state.with_updates(gene_network=gn.copy())
    print(f'Gene network attached: {cell.state.gene_network is not None}')

    # Set inputs and step
    cell.state.gene_network.set_input_states({
        'Oxygen_supply': True,
        'Glucose_supply': True,
    })
    gene_states = cell.state.gene_network.step(20, mode='synchronous')
    mito2 = gene_states.get('mitoATP')
    glyco2 = gene_states.get('glycoATP')
    print(f'After step - mitoATP: {mito2}, glycoATP: {glyco2}')

    # Update cell's gene_states
    cell.state = cell.state.with_updates(gene_states=gene_states)
    mito3 = cell.state.gene_states.get('mitoATP')
    glyco3 = cell.state.gene_states.get('glycoATP')
    print(f'Cell gene_states after update: mitoATP={mito3}, glycoATP={glyco3}')

if __name__ == '__main__':
    main()

