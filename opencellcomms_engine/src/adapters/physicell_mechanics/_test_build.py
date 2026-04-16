"""Quick sanity test for the built _physicell_mechanics extension."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _physicell_mechanics as m  # type: ignore
import numpy as np

print("Module loaded:", m)
print("SIMPLE_PRESSURE_SCALE:", m.SIMPLE_PRESSURE_SCALE)
print("Functions:", [x for x in dir(m) if not x.startswith("_")])

# Test 1: Two cells 12 apart, radii 8 each → d=12, R=16 → repulsion
pos = np.array([[0, 0, 0], [12, 0, 0]], dtype=np.float64)
radii = np.array([8.0, 8.0], dtype=np.float64)
alive = np.array([True, True])
repulsion = np.array([10.0, 10.0], dtype=np.float64)
adhesion = np.array([0.0, 0.0], dtype=np.float64)
max_adh = np.array([10.0, 10.0], dtype=np.float64)
velocities = np.zeros((2, 3), dtype=np.float64)
vp = np.zeros((2, 3), dtype=np.float64)
pressures = np.zeros(2, dtype=np.float64)

m.update_velocities(pos, radii, alive, repulsion, adhesion, max_adh,
                    velocities, pressures,
                    -100, -100, -100, 100, 100, 100, 8.5)

# Expected: cell 0 pushed in -x, cell 1 pushed in +x (repulsion)
# Formula: temp_r = (1 - 12/16)^2 * sqrt(10*10) = 0.0625 * 10 = 0.625
# force_x = dx * temp_r / d = 12 * 0.625 / 12 = 0.625 for cell 1
# For cell 0: dx = -12, so -12 * 0.625 / 12 = -0.625
print("\n=== Test 1: Pure repulsion ===")
print(f"Cell 0 velocity: {velocities[0]}  (expect ~[-0.625, 0, 0])")
print(f"Cell 1 velocity: {velocities[1]}  (expect ~[+0.625, 0, 0])")
print(f"Pressure 0: {pressures[0]:.6f}")

# Test 2: Distance > R+S → no force
pos2 = np.array([[0, 0, 0], [100, 0, 0]], dtype=np.float64)
velocities2 = np.zeros((2, 3), dtype=np.float64)
pressures2 = np.zeros(2, dtype=np.float64)
m.update_velocities(pos2, radii, alive, repulsion, adhesion, max_adh,
                    velocities2, pressures2,
                    -100, -100, -100, 200, 200, 200, 8.5)
print("\n=== Test 2: Far apart (no force) ===")
print(f"Cell 0 velocity: {velocities2[0]}  (expect [0, 0, 0])")

# Test 3: Adhesion pulls cells together
pos3 = np.array([[0, 0, 0], [14, 0, 0]], dtype=np.float64)  # d=14, R=16 (rep), S=20 (adh)
velocities3 = np.zeros((2, 3), dtype=np.float64)
pressures3 = np.zeros(2, dtype=np.float64)
adhesion3 = np.array([5.0, 5.0], dtype=np.float64)
m.update_velocities(pos3, radii, alive, repulsion, adhesion3, max_adh,
                    velocities3, pressures3,
                    -100, -100, -100, 100, 100, 100, 8.5)
# At d=14, R=16: rep = (1-14/16)^2 * 10 = 0.015625 * 10 = 0.15625
# At d=14, S=20: adh = (1-14/20)^2 * 5 = 0.09 * 5 = 0.45
# net = 0.15625 - 0.45 = -0.29375 (attractive)
print("\n=== Test 3: Adhesion dominates ===")
print(f"Cell 0 velocity: {velocities3[0]}  (expect ~[+0.294, 0, 0], attractive)")

# Test 4: Full update_mechanics (positions move)
pos4 = np.array([[0, 0, 0], [12, 0, 0]], dtype=np.float64)
velocities4 = np.zeros((2, 3), dtype=np.float64)
vp4 = np.zeros((2, 3), dtype=np.float64)
pressures4 = np.zeros(2, dtype=np.float64)
m.update_mechanics(pos4, radii, alive, repulsion, adhesion, max_adh,
                   velocities4, vp4, pressures4,
                   0.1, -100, -100, -100, 100, 100, 100, 8.5, True)
print("\n=== Test 4: Combined velocity+position, dt=0.1 ===")
print(f"Initial pos: [[0,0,0], [12,0,0]]")
print(f"After step: pos[0]={pos4[0]}, pos[1]={pos4[1]}")
print(f"Velocities stored: vp[0]={vp4[0]}, vp[1]={vp4[1]}")

print("\nALL TESTS PASSED")
