# Z Slice Selection Feature for FiPy H5 Reader

## 🎯 **Feature Added**

Added a `--z-slice` command line flag to manually specify which Z slice to visualize in the 3D domain, providing full control over the visualization plane.

### **New Command Line Argument:**
```bash
--z-slice Z_SLICE     Z slice index to visualize (default: auto-select slice with most cells)
```

---

## ✅ **Implementation Details**

### **1. Command Line Argument:**
```python
parser.add_argument('--z-slice', type=int, default=None,
                   help='Z slice index to visualize (default: auto-select slice with most cells)')
```

### **2. Updated plot_results Method:**
```python
def plot_results(self, substance_name: str, save_path: str = None, z_slice: int = None):
    """Plot simulation results"""
```

### **3. Z Slice Selection Logic:**
```python
if z_slice is not None:
    # User specified Z slice
    middle_z = z_slice
    print(f"[*] Using user-specified Z slice {middle_z}")
    
    # Validate slice is within bounds
    if middle_z < 0 or middle_z >= nz:
        print(f"[!] Warning: Z slice {middle_z} is outside valid range [0, {nz-1}]")
        middle_z = max(0, min(middle_z, nz-1))
        print(f"[*] Clamped to Z slice {middle_z}")
else:
    # Auto-select slice with most cells (existing behavior)
    # ... existing auto-selection logic ...
```

### **4. Bounds Checking:**
- **Validates** Z slice is within valid range [0, nz-1]
- **Clamps** invalid values to nearest valid slice
- **Reports** warnings for out-of-bounds values

---

## 🧪 **Usage Examples**

### **Auto-Selection Mode (Default):**
```bash
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py tools/generated_h5/tumor_core3.h5 --domain-size 2000e-6 --grid-size 40

# Output:
# [*] Cell distribution by Z slice:
#     Z=12: 1 cells
#     Z=13: 1 cells
#     ...
#     Z=20: 22 cells  ← Most cells
#     ...
# [*] Auto-selected Z slice 20 (contains 22 cells)
# [*] Plotted 41 cells
```

### **Manual Z Slice Selection:**
```bash
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py tools/generated_h5/tumor_core3.h5 --domain-size 2000e-6 --grid-size 40 --z-slice 15

# Output:
# [*] Using user-specified Z slice 15
# [*] Plotted 12 cells
```

### **Different Z Slice:**
```bash
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py tools/generated_h5/tumor_core3.h5 --domain-size 2000e-6 --grid-size 40 --z-slice 25

# Output:
# [*] Using user-specified Z slice 25
# [*] Plotted 10 cells
```

### **Bounds Checking:**
```bash
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py tools/generated_h5/tumor_core3.h5 --domain-size 2000e-6 --grid-size 40 --z-slice 50

# Output:
# [*] Using user-specified Z slice 50
# [!] Warning: Z slice 50 is outside valid range [0, 39]
# [*] Clamped to Z slice 39
# [!] No cells found in slice 39 ± 1
```

---

## 📊 **Test Results**

| Z Slice | Mode | Cells Plotted | Status |
|---------|------|---------------|---------|
| Auto (20) | Auto-select | 41 cells | ✅ Optimal |
| 15 | Manual | 12 cells | ✅ Valid |
| 25 | Manual | 10 cells | ✅ Valid |
| 50 | Manual | 0 cells | ✅ Clamped to 39 |

---

## 🎯 **Key Benefits**

### **1. Flexible Visualization:**
- **✅ MANUAL**: Specify exact Z slice for targeted analysis
- **✅ AUTO**: Automatically find slice with most cells
- **✅ EXPLORATION**: Easily explore different Z levels

### **2. Robust Error Handling:**
- **✅ BOUNDS**: Validates Z slice is within valid range
- **✅ CLAMPING**: Automatically corrects invalid values
- **✅ FEEDBACK**: Clear warnings for out-of-bounds inputs

### **3. Scientific Utility:**
- **✅ ANALYSIS**: Compare substance distributions at different Z levels
- **✅ VALIDATION**: Verify 3D structure by examining multiple slices
- **✅ PRESENTATION**: Create specific views for publications

---

## 🔧 **Technical Implementation**

### **Z Slice Coordinate System:**
- **Grid indices**: 0 to nz-1 (where nz is grid size in Z direction)
- **Physical coordinates**: Automatically mapped to correct domain bounds
- **Cell selection**: Shows cells in slice ± 1 for visibility

### **Cell Plotting Logic:**
```python
# Convert Z to grid index for slice selection
z_idx = int((z_meters + self.domain_size/2) / (self.domain_size / nz))

# Show cells in the selected slice (±1 for visibility)
if abs(z_idx - middle_z) <= 1:
    cell_x_coords.append(x_um)
    cell_y_coords.append(y_um)
```

### **Slice Selection Priority:**
1. **User-specified** (--z-slice flag)
2. **Auto-selected** (slice with most cells)
3. **Default fallback** (middle slice nz//2)

---

## 📋 **Usage Guidelines**

### **For Exploration:**
```bash
# Start with auto-selection to find interesting slices
python script.py file.h5 --domain-size 2000e-6 --grid-size 40

# Then explore specific slices
python script.py file.h5 --domain-size 2000e-6 --grid-size 40 --z-slice 15
python script.py file.h5 --domain-size 2000e-6 --grid-size 40 --z-slice 20
python script.py file.h5 --domain-size 2000e-6 --grid-size 40 --z-slice 25
```

### **For Analysis:**
```bash
# Compare top, middle, and bottom slices
python script.py file.h5 --z-slice 5   # Bottom
python script.py file.h5 --z-slice 20  # Middle  
python script.py file.h5 --z-slice 35  # Top
```

### **For Validation:**
```bash
# Check if cells are properly distributed in 3D
for z in {10..30..5}; do
    python script.py file.h5 --z-slice $z
done
```

---

## ✅ **Results Summary**

### **Feature Complete:**
- **✅ IMPLEMENTED**: Z slice selection flag added
- **✅ TESTED**: Works with manual and auto-selection modes
- **✅ ROBUST**: Proper bounds checking and error handling
- **✅ DOCUMENTED**: Clear help text and examples

### **User Experience:**
- **✅ INTUITIVE**: Simple --z-slice flag
- **✅ FLEXIBLE**: Auto-select or manual specification
- **✅ SAFE**: Automatic bounds checking and clamping
- **✅ INFORMATIVE**: Clear feedback on slice selection

### **Scientific Value:**
- **✅ EXPLORATION**: Easy to explore different Z levels
- **✅ ANALYSIS**: Compare substance distributions across slices
- **✅ VALIDATION**: Verify 3D cell distribution
- **✅ PRESENTATION**: Create targeted visualizations

**The Z slice selection feature provides complete control over 3D domain visualization!** 🚀

---

## 🔍 **Quick Reference**

```bash
# Auto-select best slice (default)
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5

# Specify Z slice manually
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --z-slice 15

# Combined with domain settings
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --domain-size 2000e-6 --grid-size 40 --z-slice 20

# Show help
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py --help
```
