
import sys
sys.path.append('tests/jayatilake_experiment')
from jayatilake_experiment_custom_functions import calculate_cell_metabolism

# Create mock config with required parameters
class MockConfig:
    def __init__(self):
        self.custom_parameters = {
            'the_optimal_oxygen': 0.005,
            'the_optimal_glucose': 0.04,
            'the_optimal_lactate': 0.04,
            'oxygen_vmax': 1e-16,
            'glucose_vmax': 3e-15,
            'max_atp': 30,
            'proton_coefficient': 0.01,
            'tgfa_consumption_rate': 1e-17,
            'tgfa_production_rate': 0.0,
            'hgf_consumption_rate': 1e-17,
            'hgf_production_rate': 0.0,
            'fgf_consumption_rate': 1e-17,
            'fgf_production_rate': 0.0,
        }

config = MockConfig()

# Test metabolism function directly
base_cell_state = {'atp_rate': 0.0}

# Test environment with good conditions for glycolysis
local_environment = {
    'Oxygen': 0.01,    # Low oxygen (should favor glycolysis)
    'Glucose': 5.0,    # High glucose
    'Lactate': 1.0,    # Some lactate
    'H': 1e-7,         # Neutral pH
    'TGFA': 4e-5, 'HGF': 0.0, 'FGF': 0.0, 'GI': 0.0,
    'EGFRD': 0.0, 'FGFRD': 0.0, 'cMETD': 0.0, 'MCT1D': 0.0, 'GLUT1D': 0.0
}

# Test different gene states
test_cases = [
    {'name': 'Glycolysis Only', 'genes': {'glycoATP': 1.0, 'mitoATP': 0.0}},
    {'name': 'OXPHOS Only', 'genes': {'glycoATP': 0.0, 'mitoATP': 1.0}},
    {'name': 'Both Pathways', 'genes': {'glycoATP': 1.0, 'mitoATP': 1.0}},
    {'name': 'No ATP', 'genes': {'glycoATP': 0.0, 'mitoATP': 0.0}},
]

print("🧪 METABOLISM FUNCTION TEST")
print("=" * 40)

for case in test_cases:
    print(f"\n📊 {case['name']}:")
    print(f"   Gene states: {case['genes']}")

    # Create cell state with gene states
    cell_state = base_cell_state.copy()
    cell_state['gene_states'] = case['genes']

    try:
        reactions = calculate_cell_metabolism(local_environment, cell_state, config)
        
        # Show key reactions
        key_substances = ['Glucose', 'Lactate', 'Oxygen', 'H']
        for substance in key_substances:
            rate = reactions.get(substance, 0.0)
            direction = "production" if rate > 0 else "consumption" if rate < 0 else "no change"
            print(f"   {substance}: {rate:.2e} ({direction})")
            
        atp_rate = cell_state.get('atp_rate', 0.0)
        print(f"   ATP rate: {atp_rate:.2e}")
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

print("\n💡 EXPECTED RESULTS:")
print("   - Glycolysis Only: Glucose consumption, Lactate production")
print("   - OXPHOS Only: Oxygen consumption, minimal Lactate")
print("   - Both Pathways: Mixed metabolism")
print("   - No ATP: Minimal reactions")
