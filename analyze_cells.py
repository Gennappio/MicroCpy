import h5py
import numpy as np

# Load the H5 file
with h5py.File('initial_state_3D_S.h5', 'r') as f:
    positions = f['cells']['positions'][:]

print(f'Total cells: {len(positions)}')

# Parameters
cell_height = 5e-6  # 5 μm
domain_size = 500e-6  # 500 μm domain
nx = ny = nz = 25  # 25x25x25 grid
dx = dy = dz = domain_size / 25

# Convert to FiPy grid coordinates
z_coords = []
xy_coords = []
for pos in positions:
    x_meters = pos[0] * cell_height
    y_meters = pos[1] * cell_height
    z_meters = pos[2] * cell_height

    x = int(x_meters / dx)
    y = int(y_meters / dy)
    z = int(z_meters / dz)

    z_coords.append(z)
    xy_coords.append((x, y))

z_coords = np.array(z_coords)
unique_z, counts = np.unique(z_coords, return_counts=True)

print('\nCells per Z slice:')
for z, count in zip(unique_z, counts):
    print(f'  Z={z}: {count} cells')

# Find the Z slice with most cells
middle_z = unique_z[np.argmax(counts)]
print(f'\nZ slice with most cells: {middle_z} ({np.max(counts)} cells)')

# Check different slice ranges
print('\nCells in different slice ranges:')
for slice_range in [0, 1, 2, 3]:
    slice_mask = np.abs(z_coords - middle_z) <= slice_range
    cells_in_slice = np.sum(slice_mask)
    print(f'  Z={middle_z}±{slice_range}: {cells_in_slice} cells')

# Check X,Y distribution
xy_coords = np.array(xy_coords)
print(f'\nX,Y coordinate ranges:')
print(f'  X: {xy_coords[:, 0].min()} - {xy_coords[:, 0].max()}')
print(f'  Y: {xy_coords[:, 1].min()} - {xy_coords[:, 1].max()}')

# Check for overlapping cells
unique_xy = np.unique(xy_coords, axis=0)
print(f'\nUnique X,Y positions: {len(unique_xy)} (out of {len(xy_coords)} total cells)')
print(f'Cells per position: {len(xy_coords) / len(unique_xy):.1f} average')

print('\nREAL ISSUE IDENTIFIED:')
print('Multiple cells are occupying the same X,Y grid position!')
print('The 2D plot only shows unique positions, not all cells!')
