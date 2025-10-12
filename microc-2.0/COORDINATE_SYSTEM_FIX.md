# FiPy H5 Reader Coordinate System Fix

## 🎯 **Problem Identified**

The FiPy H5 reader was displaying plots with incorrect coordinate axes that didn't match the actual domain bounds.

### **Issue Details:**
- **Expected**: Domain from -1500 to +1500 μm for 3000 μm domain
- **Actual**: Plot axes showing 0 to 40 (grid indices) instead of physical coordinates
- **Root cause**: `plt.imshow()` was using default grid indices instead of physical coordinates

### **Symptoms:**
```bash
# User specified 3000 μm domain expecting -1500 to +1500 μm
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --domain-size 3000e-6
# Result: Plot showed axes from ~0 to 60 (grid indices) ❌
# Expected: Plot should show axes from -1500 to +1500 μm ✅
```

---

## ✅ **Solution Implemented**

Fixed the plotting coordinate system to display actual physical coordinates instead of grid indices.

### **Key Changes:**

#### **1. Added Extent Parameter to imshow():**
```python
# Calculate extent for centered domain: -domain_size/2 to +domain_size/2
half_domain = self.domain_size / 2
extent = [-half_domain*1e6, half_domain*1e6, -half_domain*1e6, half_domain*1e6]  # Convert to μm

plt.imshow(slice_data.T, origin='lower', cmap='viridis', aspect='equal', extent=extent)
```

#### **2. Updated Axis Labels:**
```python
plt.xlabel('X Coordinate (μm)')  # Was: 'X Grid Coordinate'
plt.ylabel('Y Coordinate (μm)')  # Was: 'Y Grid Coordinate'
```

#### **3. Fixed Cell Position Plotting:**
```python
for pos in positions:
    # Convert biological grid coordinates to physical coordinates (meters)
    pos_physical = pos * self.cell_height  # Convert to meters
    
    # Convert to μm for plotting (physical coordinates are already centered)
    x_um = pos_physical[0] * 1e6  # Convert to μm
    y_um = pos_physical[1] * 1e6  # Convert to μm
    
    # Plot cells at correct physical coordinates
    cell_x_coords.append(x_um)
    cell_y_coords.append(y_um)
```

#### **4. Fixed Legend Display:**
```python
if cell_x_coords:
    plt.scatter(cell_x_coords, cell_y_coords, ...)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')  # Only show when cells exist
```

---

## 🧪 **Test Results**

### **Before Fix:**
```bash
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --domain-size 3000e-6
# Plot axes: 0 to 60 (grid indices) ❌
# Confusing and incorrect coordinate system ❌
```

### **After Fix:**
```bash
# 2000 μm domain
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --domain-size 2000e-6 --grid-size 40
# ✅ Domain bounds: -1000 to 1000 μm
# ✅ Plot axes: -1000 to +1000 μm
# ✅ Correct physical coordinates

# 3000 μm domain  
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --domain-size 3000e-6 --grid-size 60
# ✅ Domain bounds: -1500 to 1500 μm
# ✅ Plot axes: -1500 to +1500 μm
# ✅ Correct physical coordinates
```

---

## 📊 **Coordinate System Comparison**

| Domain Size | Expected Bounds | Plot Axes Before | Plot Axes After | Status |
|-------------|-----------------|------------------|------------------|---------|
| 1000 μm | -500 to +500 μm | 0 to 25 | -500 to +500 μm | ✅ Fixed |
| 2000 μm | -1000 to +1000 μm | 0 to 40 | -1000 to +1000 μm | ✅ Fixed |
| 3000 μm | -1500 to +1500 μm | 0 to 60 | -1500 to +1500 μm | ✅ Fixed |

---

## 🎯 **Key Benefits**

### **1. Intuitive Coordinates:**
- **✅ PHYSICAL**: Axes show actual physical distances in μm
- **✅ CENTERED**: Domain properly centered at origin
- **✅ CONSISTENT**: Matches user expectations

### **2. Scientific Accuracy:**
- **✅ REALISTIC**: Cell positions at correct physical locations
- **✅ MEASURABLE**: Can directly read distances from plot
- **✅ COMPARABLE**: Consistent with other simulation tools

### **3. User Experience:**
- **✅ CLEAR**: No confusion about coordinate system
- **✅ PREDICTABLE**: Domain size matches plot bounds
- **✅ PROFESSIONAL**: Publication-ready plots

---

## 🔧 **Technical Details**

### **Extent Parameter:**
The `extent` parameter in `plt.imshow()` defines the physical coordinates:
```python
extent = [left, right, bottom, top]  # Physical coordinates
# For 3000 μm domain: [-1500, 1500, -1500, 1500]
```

### **Coordinate Transformation:**
```python
# Grid indices: 0, 1, 2, ..., nx-1
# Physical coords: -domain_size/2, ..., 0, ..., +domain_size/2
physical_coord = (grid_index / nx - 0.5) * domain_size
```

### **Cell Position Mapping:**
```python
# Biological grid → Physical meters → Plot μm
pos_physical = pos * cell_height  # Grid to meters
pos_plot = pos_physical * 1e6     # Meters to μm
```

---

## 📋 **Usage Examples**

### **Small Domain (1000 μm):**
```bash
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --domain-size 1000e-6 --grid-size 25
# Plot: -500 to +500 μm
```

### **Medium Domain (2000 μm):**
```bash
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --domain-size 2000e-6 --grid-size 40
# Plot: -1000 to +1000 μm
```

### **Large Domain (3000 μm):**
```bash
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --domain-size 3000e-6 --grid-size 60
# Plot: -1500 to +1500 μm
```

### **Custom Domain (4000 μm):**
```bash
python benchmarks/standalone_steadystate_fipy_3D_h5_reader.py file.h5 --domain-size 4000e-6 --grid-size 80
# Plot: -2000 to +2000 μm
```

---

## ✅ **Results Summary**

### **Problem Solved:**
- **✅ ACCURATE**: Plot coordinates match actual domain bounds
- **✅ INTUITIVE**: Domain size directly corresponds to plot range
- **✅ CONSISTENT**: Works for any domain size
- **✅ PROFESSIONAL**: Clean, publication-ready visualizations

### **User Experience:**
- **✅ PREDICTABLE**: `--domain-size 3000e-6` → plot from -1500 to +1500 μm
- **✅ CLEAR**: Physical coordinates in μm on both axes
- **✅ SCIENTIFIC**: Accurate spatial representation of simulation

### **Technical Quality:**
- **✅ ROBUST**: Works with any domain size and grid resolution
- **✅ EFFICIENT**: No performance impact
- **✅ MAINTAINABLE**: Clean, well-documented code

**The FiPy H5 reader now displays exactly the coordinate system you expect!** 🚀

---

## 🔍 **Verification**

To verify the fix is working correctly:

1. **Check console output:**
   ```
   Domain bounds: -1500 to 1500 μm  # Should match your expectation
   ```

2. **Check plot axes:**
   - X-axis should go from -domain_size/2 to +domain_size/2 μm
   - Y-axis should go from -domain_size/2 to +domain_size/2 μm

3. **Check cell positions:**
   - Red dots should appear at correct physical locations
   - Cell coordinates should make physical sense

**Now when you specify `--domain-size 3000e-6`, the plot axes will correctly show -1500 to +1500 μm!** ✅
