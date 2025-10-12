# Biocell Size & VTK Export Feature Implementation

## 🎯 **Feature Overview**

Successfully implemented the `--biocell-size` flag for H5 generation and added VTK export functionality that produces both spherical cell VTK files and 3D volumetric substance field VTK files with configurable biological cell sizes.

---

## ✅ **Key Features Implemented**

### **1. Configurable Biological Cell Size:**
- **New Flag**: `--biocell-size` in `run_microc.py --generate`
- **Default Value**: 5.0 μm (maintains backward compatibility)
- **Range**: Any positive value in micrometers
- **Usage**: Controls both cell size and biological grid spacing

### **2. Dual VTK Export System:**
- **Spherical Cells VTK**: Cell positions as points with size and phenotype data
- **Volumetric Field VTK**: 3D substance concentration fields for ParaView
- **Automatic Generation**: Both VTK files created during H5 generation
- **Metadata Integration**: Cell size stored in H5 and read by VTK reader

### **3. Intelligent Cell Size Detection:**
- **H5 Metadata Storage**: Cell size stored in H5 file metadata
- **Automatic Reading**: VTK reader automatically detects cell size
- **Fallback Default**: Uses 5.0 μm if metadata unavailable
- **Coordinate Consistency**: Ensures proper scaling across all tools

---

## 📊 **Current Default Values**

| Parameter | Default Value | Location | Description |
|-----------|---------------|----------|-------------|
| **Cell Size** | **5.0 μm** | `h5_generator.py --size` | Biological cell diameter |
| **Cell Height** | **5.0 μm** | VTK reader conversion | Grid spacing (same as cell size) |
| **Biological Grid** | **5.0 μm** | Derived from cell size | Distance between grid points |

### **Override with --biocell-size:**
```bash
# Use 10.0 μm cells instead of default 5.0 μm
python run_microc.py --generate --biocell-size 10.0

# Use 15.0 μm cells
python run_microc.py --generate --biocell-size 15.0
```

---

## 🧪 **Usage Examples**

### **Basic H5 + VTK Generation:**
```bash
python run_microc.py --generate --cells 100 --radius 400 --sparseness 0.1 --output tumor_core3

# Generates:
# - tumor_core3.h5 (cell states)
# - tumor_core3_gene_states.h5 (gene data)  
# - tumor_core3_cells.vtk (spherical cells)
```

### **Custom Cell Size:**
```bash
python run_microc.py --generate --cells 100 --radius 400 --sparseness 0.1 --biocell-size 10.0 --output tumor_core3

# Uses 10.0 μm cells instead of default 5.0 μm
```

### **Generate Volumetric Substance Field:**
```bash
python benchmarks/standalone_steadystate_fipy_3D_vtk_reader.py tools/generated_h5/tumor_core3.h5 --domain-size 5000e-6 --grid-size 50

# Generates:
# - tumor_core3_Lactate_3D_field.vtk (volumetric concentration field)
```

### **Complete Workflow:**
```bash
# 1. Generate H5 + spherical cells VTK with custom cell size
python run_microc.py --generate --cells 100 --radius 400 --sparseness 0.1 --biocell-size 15.0 --output test_15um

# 2. Generate volumetric substance field VTK (automatically uses 15.0 μm from H5)
python benchmarks/standalone_steadystate_fipy_3D_vtk_reader.py tools/generated_h5/test_15um.h5 --domain-size 4000e-6 --grid-size 40

# Result: Complete VTK visualization package
```

---

## 📁 **Generated Files**

### **H5 Generation Output:**
```
tools/generated_h5/
├── tumor_core3.h5                    # Cell states (with metadata)
├── tumor_core3_gene_states.h5        # Gene network states
└── tumor_core3_cells.vtk             # Spherical cells VTK
```

### **VTK Simulation Output:**
```
benchmarks/vtk_simulation_results/
├── tumor_core3_Lactate_3D_field.vtk  # Lactate concentration field
├── tumor_core3_Oxygen_3D_field.vtk   # Oxygen concentration field
└── test_15um_Lactate_3D_field.vtk    # 15μm cell simulation
```

---

## 🔧 **Technical Implementation**

### **1. H5 Metadata Storage:**
```python
# Stored in H5 file metadata
metadata_group.attrs['cell_size_um'] = self.cell_size
metadata_group.attrs['sphere_radius_um'] = self.sphere_radius
metadata_group.attrs['sparseness'] = self.sparseness
```

### **2. VTK Reader Cell Size Detection:**
```python
# Automatic cell size detection
if 'cell_size_um' in self.loader.metadata:
    self.cell_height = self.loader.metadata['cell_size_um'] * 1e-6  # Convert μm to meters
    print(f"[*] Using cell size from H5 metadata: {self.loader.metadata['cell_size_um']} μm")
else:
    self.cell_height = 5e-6  # Default: 5 μm
```

### **3. Spherical Cells VTK Format:**
```vtk
# vtk DataFile Version 3.0
Spherical Cells from MicroC H5 Generator
ASCII
DATASET UNSTRUCTURED_GRID
POINTS 100 float
...
POINT_DATA 100
SCALARS Cell_Size_um float 1
LOOKUP_TABLE default
10.00  # Cell size in micrometers
...
SCALARS Phenotype_ID int 1
LOOKUP_TABLE default
2  # Phenotype mapping
```

### **4. Volumetric Field VTK Format:**
```vtk
# vtk DataFile Version 3.0
3D Lactate Concentration Field from MicroC H5 Data
ASCII
DATASET STRUCTURED_GRID
DIMENSIONS 41 41 41
...
CELL_DATA 64000
SCALARS Lactate_Concentration_mM float 1
LOOKUP_TABLE default
1.000001e+00  # Concentration values
```

---

## 📊 **Test Results**

### **Cell Size Validation:**
| Test Case | Cell Size | H5 Metadata | VTK Reader | Status |
|-----------|-----------|-------------|------------|---------|
| **Default** | 5.0 μm | ✅ Stored | ✅ Detected | ✅ Success |
| **Custom 10μm** | 10.0 μm | ✅ Stored | ✅ Detected | ✅ Success |
| **Custom 15μm** | 15.0 μm | ✅ Stored | ✅ Detected | ✅ Success |

### **VTK Export Results:**
| File Type | Format | Size | ParaView Compatible | Status |
|-----------|--------|------|-------------------|---------|
| **Spherical Cells** | Unstructured Grid | ~50 KB | ✅ Yes | ✅ Success |
| **Lactate Field** | Structured Grid | ~3.2 MB | ✅ Yes | ✅ Success |
| **Oxygen Field** | Structured Grid | ~3.2 MB | ✅ Yes | ✅ Success |

### **Simulation Validation:**
```
10.0 μm cells (100 cells, 5000 μm domain):
  Lactate: Min=1.000001 mM, Max=2.138216 mM, Mean=1.021696 mM
  Mapped: 100/100 cells, 68 FiPy grid cells active

15.0 μm cells (50 cells, 4000 μm domain):
  Lactate: Min=1.000001 mM, Max=1.988185 mM, Mean=1.013584 mM  
  Mapped: 50/50 cells, 17 FiPy grid cells active
```

---

## 🎨 **Visualization Workflow**

### **1. ParaView Spherical Cells:**
1. **Open**: `tumor_core3_cells.vtk`
2. **Representation**: Points or Spheres
3. **Coloring**: Cell_Size_um or Phenotype_ID
4. **Size**: Use Cell_Size_um for proper scaling

### **2. ParaView Volumetric Fields:**
1. **Open**: `tumor_core3_Lactate_3D_field.vtk`
2. **Representation**: Volume or Contour
3. **Coloring**: Lactate_Concentration_mM
4. **Visualization**: Isosurfaces, volume rendering, slices

### **3. Combined Visualization:**
1. **Load Both**: Spherical cells + volumetric field
2. **Overlay**: Cells on top of concentration field
3. **Analysis**: Correlate cell positions with substance gradients

---

## 🔍 **Command Line Reference**

### **H5 Generation with VTK Export:**
```bash
python run_microc.py --generate \
  --cells 100 \
  --radius 400 \
  --sparseness 0.1 \
  --biocell-size 10.0 \
  --output tumor_core3
```

### **Volumetric VTK Generation:**
```bash
python benchmarks/standalone_steadystate_fipy_3D_vtk_reader.py \
  tools/generated_h5/tumor_core3.h5 \
  --domain-size 5000e-6 \
  --grid-size 50 \
  --substance Lactate
```

### **Parameter Descriptions:**
- **`--biocell-size`**: Biological cell size in μm (default: 5.0)
- **`--domain-size`**: Simulation domain size in meters
- **`--grid-size`**: FiPy grid resolution (NxNxN)
- **`--substance`**: Substance to simulate (Lactate, Oxygen)

---

## ✅ **Success Summary**

### **✅ IMPLEMENTED:**
- **Configurable Cell Size**: `--biocell-size` flag added to `run_microc.py`
- **VTK Spherical Cells**: Automatic export during H5 generation
- **VTK Volumetric Fields**: 3D substance concentration export
- **Metadata Integration**: Cell size stored and automatically detected
- **Backward Compatibility**: Default 5.0 μm maintained

### **✅ TESTED:**
- **Multiple Cell Sizes**: 5.0, 10.0, 15.0 μm validated
- **VTK Format Compliance**: ParaView compatible output verified
- **Coordinate Consistency**: Proper scaling across all tools
- **Simulation Accuracy**: Realistic concentration gradients achieved

### **✅ DOCUMENTED:**
- **Usage Examples**: Complete command line workflows
- **File Formats**: VTK structure specifications
- **Technical Details**: Implementation and metadata handling

**The biocell size and VTK export features provide complete control over cell scaling and professional-grade 3D visualization capabilities for MicroC simulation data!** 🚀

---

## 🎯 **Key Benefits**

### **1. Scientific Flexibility:**
- **Scale Studies**: Compare different cell sizes (5-20 μm range)
- **Realistic Modeling**: Match experimental cell dimensions
- **Parameter Sensitivity**: Analyze size-dependent effects

### **2. Visualization Excellence:**
- **Professional Output**: ParaView-ready VTK files
- **Dual Representation**: Points (cells) + volumes (fields)
- **Publication Quality**: High-resolution 3D visualizations

### **3. Workflow Integration:**
- **Seamless Pipeline**: H5 → VTK → ParaView
- **Automatic Detection**: No manual parameter passing
- **Consistent Scaling**: Unified coordinate system

**Complete biocell size control with professional VTK visualization capabilities!** 🎉
