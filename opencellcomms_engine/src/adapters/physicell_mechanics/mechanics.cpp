// Copyright (c) 2026 OpenCellComms contributors.
// PhysiCell-faithful cell mechanics kernel, pybind11 bindings.
//
// Implements:
//  - Cell-cell repulsion:  temp_r = (1 - d/R)^2 * sqrt(cr_i * cr_j)
//  - Cell-cell adhesion:   temp_a = (1 - d/S)^2 * sqrt(ca_i * ca_j)
//  - Force: f_ij = (temp_r - temp_a) / d * (r_i - r_j)
//  - Pressure: sum (1 - d/R)^2 / simple_pressure_scale
//  - Adams-Bashforth position integration
//
// All input/output is via NumPy views (zero-copy).

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <cmath>
#include <algorithm>
#include <vector>
#include <cstdint>

namespace py = pybind11;

// PhysiCell constant: 12 * (1 - sqrt(pi/(2*sqrt(3))))^2
static constexpr double SIMPLE_PRESSURE_SCALE = 0.027288820670331;

// ── Helper: uniform grid neighbor search ───────────────────────────────
// Returns for each cell its list of neighbor cell indices (within max cutoff).
// Uses a flat voxel hash grid; voxel side = cutoff_radius.
struct UniformGrid {
    double voxel_size;
    double x_min, y_min, z_min;
    int nx, ny, nz;
    std::vector<std::vector<int>> voxels;  // voxel_idx -> list of cell idxs

    UniformGrid(double cell_size,
                double x0, double y0, double z0,
                double x1, double y1, double z1) {
        voxel_size = cell_size;
        x_min = x0; y_min = y0; z_min = z0;
        nx = std::max(1, (int)std::ceil((x1 - x0) / cell_size));
        ny = std::max(1, (int)std::ceil((y1 - y0) / cell_size));
        nz = std::max(1, (int)std::ceil((z1 - z0) / cell_size));
        voxels.resize((size_t)nx * ny * nz);
    }

    inline int voxel_of(double x, double y, double z) const {
        int ix = std::min(nx - 1, std::max(0, (int)((x - x_min) / voxel_size)));
        int iy = std::min(ny - 1, std::max(0, (int)((y - y_min) / voxel_size)));
        int iz = std::min(nz - 1, std::max(0, (int)((z - z_min) / voxel_size)));
        return (iz * ny + iy) * nx + ix;
    }

    void insert(int cell_idx, double x, double y, double z) {
        voxels[voxel_of(x, y, z)].push_back(cell_idx);
    }

    // Fill `out` with indices of cells in the 27 Moore neighbors of (x,y,z).
    void moore_neighbors(double x, double y, double z,
                         std::vector<int>& out) const {
        int ix = std::min(nx - 1, std::max(0, (int)((x - x_min) / voxel_size)));
        int iy = std::min(ny - 1, std::max(0, (int)((y - y_min) / voxel_size)));
        int iz = std::min(nz - 1, std::max(0, (int)((z - z_min) / voxel_size)));
        for (int dz = -1; dz <= 1; ++dz) {
            int jz = iz + dz;
            if (jz < 0 || jz >= nz) continue;
            for (int dy = -1; dy <= 1; ++dy) {
                int jy = iy + dy;
                if (jy < 0 || jy >= ny) continue;
                for (int dx = -1; dx <= 1; ++dx) {
                    int jx = ix + dx;
                    if (jx < 0 || jx >= nx) continue;
                    int vi = (jz * ny + jy) * nx + jx;
                    for (int c : voxels[vi]) out.push_back(c);
                }
            }
        }
    }
};

// ── Main kernel: compute velocities from pairwise forces ───────────────
// Inputs (NumPy arrays, all length N or shape (N,3)):
//  positions        (N, 3) float64
//  radii            (N,)   float64
//  alive            (N,)   bool
//  repulsion        (N,)   float64 — cell_cell_repulsion_strength
//  adhesion         (N,)   float64 — cell_cell_adhesion_strength
//  max_adh_distance (N,)   float64 — relative_maximum_adhesion_distance * radius
//  velocities       (N, 3) float64 — OUTPUT (overwritten)
//  pressures        (N,)   float64 — OUTPUT (overwritten)
// Parameters:
//  domain bounds (x_min, y_min, z_min, x_max, y_max, z_max)
//  max_cell_radius — voxel size for neighbor grid

static void update_velocities(
    py::array_t<double, py::array::c_style | py::array::forcecast> positions,
    py::array_t<double, py::array::c_style | py::array::forcecast> radii,
    py::array_t<bool,   py::array::c_style | py::array::forcecast> alive,
    py::array_t<double, py::array::c_style | py::array::forcecast> repulsion,
    py::array_t<double, py::array::c_style | py::array::forcecast> adhesion,
    py::array_t<double, py::array::c_style | py::array::forcecast> max_adh_distance,
    py::array_t<double, py::array::c_style> velocities,
    py::array_t<double, py::array::c_style> pressures,
    double x_min, double y_min, double z_min,
    double x_max, double y_max, double z_max,
    double max_cell_radius
) {
    const ssize_t N = positions.shape(0);
    if (positions.shape(1) != 3) throw std::runtime_error("positions must be (N,3)");
    if (velocities.shape(0) != N || velocities.shape(1) != 3)
        throw std::runtime_error("velocities must be (N,3)");

    const double* __restrict pos = positions.data();
    const double* __restrict R   = radii.data();
    const bool*   __restrict al  = alive.data();
    const double* __restrict cr  = repulsion.data();
    const double* __restrict ca  = adhesion.data();
    const double* __restrict S   = max_adh_distance.data();
    double*       __restrict vel = velocities.mutable_data();
    double*       __restrict pr  = pressures.mutable_data();

    // Zero velocities and pressures for alive cells
    for (ssize_t i = 0; i < N; ++i) {
        vel[3*i + 0] = 0.0;
        vel[3*i + 1] = 0.0;
        vel[3*i + 2] = 0.0;
        pr[i] = 0.0;
    }

    // Build uniform grid with voxel size = 2 * max_radius * max_adh_factor
    // We assume S[i] <= 2 * max_cell_radius for typical PhysiCell params
    double voxel_size = std::max(2.0 * max_cell_radius, 10.0);
    UniformGrid grid(voxel_size, x_min, y_min, z_min, x_max, y_max, z_max);
    for (ssize_t i = 0; i < N; ++i) {
        if (!al[i]) continue;
        grid.insert((int)i, pos[3*i], pos[3*i+1], pos[3*i+2]);
    }

    // Compute forces
    std::vector<int> neighbors;
    neighbors.reserve(64);
    for (ssize_t i = 0; i < N; ++i) {
        if (!al[i]) continue;
        neighbors.clear();
        grid.moore_neighbors(pos[3*i], pos[3*i+1], pos[3*i+2], neighbors);

        for (int jn : neighbors) {
            const ssize_t j = jn;
            if (j == i || !al[j]) continue;

            double dx = pos[3*i]   - pos[3*j];
            double dy = pos[3*i+1] - pos[3*j+1];
            double dz = pos[3*i+2] - pos[3*j+2];
            double d2 = dx*dx + dy*dy + dz*dz;
            double d  = std::sqrt(d2);
            if (d < 1e-5) d = 1e-5;

            // Repulsion
            double Rsum = R[i] + R[j];
            double temp_r = 0.0;
            if (d < Rsum) {
                double u = 1.0 - d / Rsum;
                temp_r = u * u;
                pr[i] += temp_r / SIMPLE_PRESSURE_SCALE;
            }
            double eff_rep = std::sqrt(cr[i] * cr[j]);
            temp_r *= eff_rep;

            // Adhesion
            double Smax = S[i] + S[j];
            double temp_a = 0.0;
            if (d < Smax) {
                double u = 1.0 - d / Smax;
                temp_a = u * u;
                double eff_adh = std::sqrt(ca[i] * ca[j]);
                temp_a *= eff_adh;
            }

            double temp_net = temp_r - temp_a;
            if (std::fabs(temp_net) < 1e-16) continue;
            temp_net /= d;
            vel[3*i + 0] += dx * temp_net;
            vel[3*i + 1] += dy * temp_net;
            vel[3*i + 2] += dz * temp_net;
        }
    }
}


// ── Adams-Bashforth position integration ────────────────────────────────
// PhysiCell uses 2nd-order Adams-Bashforth:
//   x_new = x + dt * (1.5 * v_new - 0.5 * v_prev)
// On the first step (v_prev = 0), this reduces to x + 1.5*dt*v_new.
// After update, v_prev is set to v_new for the next step.
static void update_positions(
    py::array_t<double, py::array::c_style> positions,
    py::array_t<double, py::array::c_style | py::array::forcecast> velocities,
    py::array_t<double, py::array::c_style> velocities_prev,
    py::array_t<bool,   py::array::c_style | py::array::forcecast> alive,
    double dt,
    double x_min, double y_min, double z_min,
    double x_max, double y_max, double z_max,
    bool use_2D
) {
    const ssize_t N = positions.shape(0);
    double* __restrict pos = positions.mutable_data();
    const double* __restrict v    = velocities.data();
    double* __restrict vp   = velocities_prev.mutable_data();
    const bool*   __restrict al   = alive.data();

    for (ssize_t i = 0; i < N; ++i) {
        if (!al[i]) continue;
        for (int k = 0; k < 3; ++k) {
            if (use_2D && k == 2) continue;
            double new_v = v[3*i + k];
            double old_v = vp[3*i + k];
            pos[3*i + k] += dt * (1.5 * new_v - 0.5 * old_v);
            vp[3*i + k] = new_v;
        }
        // Clamp to domain
        if (pos[3*i]   < x_min) pos[3*i]   = x_min;
        if (pos[3*i]   > x_max) pos[3*i]   = x_max;
        if (pos[3*i+1] < y_min) pos[3*i+1] = y_min;
        if (pos[3*i+1] > y_max) pos[3*i+1] = y_max;
        if (!use_2D) {
            if (pos[3*i+2] < z_min) pos[3*i+2] = z_min;
            if (pos[3*i+2] > z_max) pos[3*i+2] = z_max;
        }
    }
}

// ── Combined: velocities + positions in one call ───────────────────────
static void update_mechanics(
    py::array_t<double, py::array::c_style> positions,
    py::array_t<double, py::array::c_style | py::array::forcecast> radii,
    py::array_t<bool,   py::array::c_style | py::array::forcecast> alive,
    py::array_t<double, py::array::c_style | py::array::forcecast> repulsion,
    py::array_t<double, py::array::c_style | py::array::forcecast> adhesion,
    py::array_t<double, py::array::c_style | py::array::forcecast> max_adh_distance,
    py::array_t<double, py::array::c_style> velocities,
    py::array_t<double, py::array::c_style> velocities_prev,
    py::array_t<double, py::array::c_style> pressures,
    double dt,
    double x_min, double y_min, double z_min,
    double x_max, double y_max, double z_max,
    double max_cell_radius,
    bool use_2D
) {
    update_velocities(
        positions, radii, alive, repulsion, adhesion, max_adh_distance,
        velocities, pressures,
        x_min, y_min, z_min, x_max, y_max, z_max, max_cell_radius
    );
    update_positions(
        positions, velocities, velocities_prev, alive, dt,
        x_min, y_min, z_min, x_max, y_max, z_max, use_2D
    );
}

// ── pybind11 module ────────────────────────────────────────────────────
PYBIND11_MODULE(_physicell_mechanics, m) {
    m.doc() = "PhysiCell-faithful cell mechanics (pybind11 C++ extension)";
    m.attr("SIMPLE_PRESSURE_SCALE") = SIMPLE_PRESSURE_SCALE;

    m.def("update_velocities", &update_velocities,
          "Compute per-cell velocities from pairwise repulsion+adhesion forces.",
          py::arg("positions"), py::arg("radii"), py::arg("alive"),
          py::arg("repulsion"), py::arg("adhesion"), py::arg("max_adh_distance"),
          py::arg("velocities"), py::arg("pressures"),
          py::arg("x_min"), py::arg("y_min"), py::arg("z_min"),
          py::arg("x_max"), py::arg("y_max"), py::arg("z_max"),
          py::arg("max_cell_radius"));

    m.def("update_positions", &update_positions,
          "Integrate positions using 2nd-order Adams-Bashforth.",
          py::arg("positions"), py::arg("velocities"), py::arg("velocities_prev"),
          py::arg("alive"), py::arg("dt"),
          py::arg("x_min"), py::arg("y_min"), py::arg("z_min"),
          py::arg("x_max"), py::arg("y_max"), py::arg("z_max"),
          py::arg("use_2D"));

    m.def("update_mechanics", &update_mechanics,
          "Combined: velocities + positions in one call.",
          py::arg("positions"), py::arg("radii"), py::arg("alive"),
          py::arg("repulsion"), py::arg("adhesion"), py::arg("max_adh_distance"),
          py::arg("velocities"), py::arg("velocities_prev"), py::arg("pressures"),
          py::arg("dt"),
          py::arg("x_min"), py::arg("y_min"), py::arg("z_min"),
          py::arg("x_max"), py::arg("y_max"), py::arg("z_max"),
          py::arg("max_cell_radius"), py::arg("use_2D"));
}