# Custom Functions and Gene Manipulation Guide

## Overview

MicroC supports custom functions for specialized simulation behaviors, including gene knockdown, overexpression, and dynamic interventions. This guide covers implementation and gene manipulation techniques.

## Custom Function Framework

### Function Registration
Custom functions are registered via the hook system and can override default behaviors.

```python
from interfaces.hooks import get_hook_manager

@get_hook_manager().register("custom_update_gene_network")
def my_gene_network_function(current_states, inputs, network_params):
    """Custom gene network update function."""
    # Your custom logic here
    return updated_states
```

### Available Hook Points
- `custom_update_gene_network` - Gene network updates
- `custom_cell_division` - Cell division logic
- `custom_cell_death` - Cell death conditions
- `custom_substance_production` - Metabolite production
- `custom_phenotype_transition` - Phenotype changes

## Gene Manipulation Techniques

### 1. Gene Knockdown (Silencing)

#### Method 1: Fixed Node States
```python
@get_hook_manager().register("custom_update_gene_network")
def gene_knockdown(current_states, inputs, network_params):
    """Knockdown specific genes by fixing them to False."""
    
    # Define knocked down genes
    knockdown_genes = ['p53', 'PTEN', 'FOXO3']
    
    # Standard network update
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    # Force knockdown genes to False
    for gene in knockdown_genes:
        if gene in updated_states:
            updated_states[gene] = False
    
    return updated_states
```

#### Method 2: Probability-Based Knockdown
```python
import random

@get_hook_manager().register("custom_update_gene_network")
def probabilistic_knockdown(current_states, inputs, network_params):
    """Knockdown with specified efficiency."""
    
    knockdown_config = {
        'p53': 0.9,      # 90% knockdown efficiency
        'PTEN': 0.8,     # 80% knockdown efficiency
        'BCL2': 0.95     # 95% knockdown efficiency
    }
    
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    for gene, efficiency in knockdown_config.items():
        if gene in updated_states and updated_states[gene]:
            # Chance to silence active gene
            if random.random() < efficiency:
                updated_states[gene] = False
    
    return updated_states
```

### 2. Gene Overexpression (Enrichment)

#### Method 1: Constitutive Expression
```python
@get_hook_manager().register("custom_update_gene_network")
def gene_overexpression(current_states, inputs, network_params):
    """Force specific genes to be constitutively active."""
    
    # Define overexpressed genes
    overexpressed_genes = ['BCL2', 'AKT', 'ERK', 'MYC']
    
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    # Force overexpressed genes to True
    for gene in overexpressed_genes:
        if gene in updated_states:
            updated_states[gene] = True
    
    return updated_states
```

#### Method 2: Enhanced Expression Probability
```python
@get_hook_manager().register("custom_update_gene_network")
def enhanced_expression(current_states, inputs, network_params):
    """Increase probability of gene activation."""
    
    enhancement_config = {
        'BCL2': 0.8,     # 80% chance to activate if conditions met
        'ERK': 0.9,      # 90% chance to activate
        'AKT': 0.85      # 85% chance to activate
    }
    
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    for gene, prob in enhancement_config.items():
        if gene in updated_states and not updated_states[gene]:
            # Chance to activate inactive gene
            if random.random() < prob:
                updated_states[gene] = True
    
    return updated_states
```

### 3. Conditional Gene Manipulation

#### Time-Dependent Interventions
```python
@get_hook_manager().register("custom_update_gene_network")
def time_dependent_knockdown(current_states, inputs, network_params):
    """Apply gene manipulation at specific time points."""
    
    current_time = network_params.get('current_time', 0)
    
    # Apply p53 knockdown after time 5.0
    if current_time > 5.0:
        knockdown_genes = ['p53', 'FOXO3']
    else:
        knockdown_genes = []
    
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    for gene in knockdown_genes:
        if gene in updated_states:
            updated_states[gene] = False
    
    return updated_states
```

#### Environment-Dependent Manipulation
```python
@get_hook_manager().register("custom_update_gene_network")
def stress_response_modification(current_states, inputs, network_params):
    """Modify gene expression based on environmental stress."""
    
    # Check oxygen levels
    oxygen_low = inputs.get('Oxygen_supply', True) == False
    
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    if oxygen_low:
        # Under hypoxia, enhance HIF1 and suppress p53
        updated_states['HIF1'] = True
        updated_states['p53'] = False
        updated_states['VEGF'] = True
    else:
        # Normal conditions, allow normal p53 function
        pass
    
    return updated_states
```

### 4. Drug Simulation

#### Targeted Therapy Simulation
```python
@get_hook_manager().register("custom_update_gene_network")
def drug_treatment(current_states, inputs, network_params):
    """Simulate targeted drug effects."""
    
    # Drug concentrations from environment
    egfr_inhibitor = inputs.get('EGFRI', False)
    pi3k_inhibitor = inputs.get('PI3KI', False)
    
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    # EGFR inhibitor effects
    if egfr_inhibitor:
        updated_states['EGFR'] = False
        updated_states['ERK'] = False  # Downstream effect
    
    # PI3K inhibitor effects
    if pi3k_inhibitor:
        updated_states['PI3K'] = False
        updated_states['AKT'] = False  # Downstream effect
        updated_states['BCL2'] = False  # Further downstream
    
    return updated_states
```

## Configuration-Based Gene Manipulation

### Mutation Files
Create mutation files to specify gene states:

```
# mutations_p53_knockout.txt
Gene_Name    Group1    Group2    Group3
p53          0.0       0.0       0.0      # Complete knockdown
PTEN         0.1       0.1       0.1      # Partial knockdown
BCL2         0.9       0.9       0.9      # Overexpression
AKT          0.8       0.8       0.8      # Enhanced expression
```

### Configuration Integration
```yaml
gene_network:
  bnd_file: "network.bnd"
  mutation_file: "mutations_p53_knockout.txt"
  propagation_steps: 50
  
  # Custom gene manipulations
  knockdown_genes: ["p53", "PTEN"]
  overexpressed_genes: ["BCL2", "MYC"]
  
  # Time-dependent interventions
  interventions:
    - time: 5.0
      action: "knockdown"
      genes: ["p53"]
    - time: 10.0
      action: "overexpress"
      genes: ["BCL2"]
```

## Advanced Gene Manipulation

### 1. Pathway-Level Interventions
```python
@get_hook_manager().register("custom_update_gene_network")
def pathway_manipulation(current_states, inputs, network_params):
    """Manipulate entire pathways."""
    
    intervention = network_params.get('pathway_intervention', None)
    
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    if intervention == "block_apoptosis":
        # Block entire apoptosis pathway
        apoptosis_genes = ['p53', 'FOXO3', 'BAX', 'PUMA']
        for gene in apoptosis_genes:
            if gene in updated_states:
                updated_states[gene] = False
        
        # Enhance survival pathway
        survival_genes = ['BCL2', 'AKT', 'ERK']
        for gene in survival_genes:
            if gene in updated_states:
                updated_states[gene] = True
    
    elif intervention == "enhance_proliferation":
        # Enhance proliferation pathway
        prolif_genes = ['MYC', 'p70', 'ERK']
        for gene in prolif_genes:
            if gene in updated_states:
                updated_states[gene] = True
        
        # Suppress growth arrest
        arrest_genes = ['p21', 'p53']
        for gene in arrest_genes:
            if gene in updated_states:
                updated_states[gene] = False
    
    return updated_states
```

### 2. Stochastic Gene Editing
```python
@get_hook_manager().register("custom_update_gene_network")
def crispr_simulation(current_states, inputs, network_params):
    """Simulate CRISPR-like gene editing with efficiency."""
    
    editing_targets = {
        'p53': {'efficiency': 0.95, 'action': 'knockout'},
        'BCL2': {'efficiency': 0.90, 'action': 'enhance'},
        'PTEN': {'efficiency': 0.85, 'action': 'knockout'}
    }
    
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    for gene, config in editing_targets.items():
        if gene in updated_states and random.random() < config['efficiency']:
            if config['action'] == 'knockout':
                updated_states[gene] = False
            elif config['action'] == 'enhance':
                updated_states[gene] = True
    
    return updated_states
```

## Implementation Example

### Complete Custom Function File
```python
# custom_gene_functions.py
from interfaces.hooks import get_hook_manager
import random

class GeneManipulator:
    def __init__(self, config):
        self.knockdown_genes = config.get('knockdown_genes', [])
        self.overexpressed_genes = config.get('overexpressed_genes', [])
        self.interventions = config.get('interventions', [])
        self.current_time = 0
    
    def update_time(self, time):
        self.current_time = time
    
    def apply_interventions(self, states):
        """Apply time-dependent interventions."""
        for intervention in self.interventions:
            if self.current_time >= intervention['time']:
                if intervention['action'] == 'knockdown':
                    for gene in intervention['genes']:
                        if gene in states:
                            states[gene] = False
                elif intervention['action'] == 'overexpress':
                    for gene in intervention['genes']:
                        if gene in states:
                            states[gene] = True
        return states

# Global manipulator instance
gene_manipulator = None

@get_hook_manager().register("custom_update_gene_network")
def comprehensive_gene_manipulation(current_states, inputs, network_params):
    """Comprehensive gene manipulation system."""
    global gene_manipulator
    
    if gene_manipulator is None:
        gene_manipulator = GeneManipulator(network_params)
    
    # Update time
    gene_manipulator.update_time(network_params.get('current_time', 0))
    
    # Standard update
    updated_states = default_gene_network_update(current_states, inputs, network_params)
    
    # Apply knockdowns
    for gene in gene_manipulator.knockdown_genes:
        if gene in updated_states:
            updated_states[gene] = False
    
    # Apply overexpression
    for gene in gene_manipulator.overexpressed_genes:
        if gene in updated_states:
            updated_states[gene] = True
    
    # Apply time-dependent interventions
    updated_states = gene_manipulator.apply_interventions(updated_states)
    
    return updated_states
```

### Usage in Configuration
```yaml
gene_network:
  bnd_file: "network.bnd"
  custom_functions: ["custom_gene_functions.py"]
  knockdown_genes: ["p53", "PTEN"]
  overexpressed_genes: ["BCL2", "AKT"]
  interventions:
    - time: 5.0
      action: "knockdown"
      genes: ["MYC"]
```

This framework provides comprehensive control over gene expression for modeling various biological scenarios including disease states, drug treatments, and genetic modifications.
