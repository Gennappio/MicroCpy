# Installation Guide

This guide covers installing OpenCellComms on Windows, macOS, and Linux.

## Prerequisites

Before installing, ensure you have the following:

| Requirement | Minimum Version | Check Command | Download |
|-------------|-----------------|---------------|----------|
| Python | 3.8+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ | `node --version` | [nodejs.org](https://nodejs.org/) |
| npm | 7+ | `npm --version` | Included with Node.js |
| Git | Any | `git --version` | [git-scm.com](https://git-scm.com/) |

## Quick Install (Recommended)

### macOS / Linux

```bash
# Clone the repository
git clone <your-repo-url>
cd OpenCellComms

# Make the installer executable and run it
chmod +x install.sh
./install.sh
```

### Windows

```batch
# Clone the repository
git clone <your-repo-url>
cd OpenCellComms

# Run the installer
install.bat
```

The installer will:
1. Check all prerequisites
2. Create a Python virtual environment (`.venv/`)
3. Install the simulation engine
4. Install Flask server dependencies
5. Install GUI (React) dependencies

## Manual Installation

If you prefer to install manually or need more control:

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd OpenCellComms
```

### Step 2: Create Python Virtual Environment

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```batch
python -m venv .venv
.venv\Scripts\activate
```

### Step 3: Install Python Engine

```bash
cd opencellcomms_engine
pip install --upgrade pip
pip install -e .
cd ..
```

### Step 4: Install Flask Server Dependencies

```bash
pip install flask flask-cors
```

### Step 5: Install GUI Dependencies

```bash
cd opencellcomms_gui
npm install
cd ..
```

## Verify Installation

### Test Python Engine

```bash
# Activate virtual environment first
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Test import
cd opencellcomms_engine
python -c "from src.workflow import executor; print('✓ Engine installed correctly')"
```

### Test GUI Build

```bash
cd opencellcomms_gui
npm run build
```

If both tests pass, installation is complete!

## Optional Dependencies

The engine supports optional features that require additional dependencies:

### Performance Optimizations
```bash
pip install numba cython joblib dask
```

### 3D Visualization
```bash
pip install mayavi vtk
```

### Jupyter Notebook Support
```bash
pip install jupyter ipykernel notebook
```

### All Optional Dependencies
```bash
cd opencellcomms_engine
pip install -e ".[all]"
```

## Platform-Specific Notes

### Windows

- Use PowerShell or Command Prompt (not WSL) for best compatibility
- If you get SSL errors, try: `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org <package>`

### macOS

- If using Apple Silicon (M1/M2/M3), all packages should work with native ARM builds
- You may need Xcode Command Line Tools: `xcode-select --install`

### Linux

- Some packages may require build tools: `sudo apt install build-essential python3-dev`
- For HDF5 support: `sudo apt install libhdf5-dev`

## Troubleshooting

### "Python not found"
- Ensure Python is in your PATH
- Try using `python3` instead of `python`

### "npm not found"
- Ensure Node.js is installed and in your PATH
- Restart your terminal after installing Node.js

### Virtual environment issues
- Delete `.venv/` and run the installer again
- Ensure you're using Python 3.8 or higher

### Permission errors on Unix
```bash
chmod +x install.sh run.sh
```

## Next Steps

After installation, see [USAGE.md](USAGE.md) for how to run OpenCellComms.

