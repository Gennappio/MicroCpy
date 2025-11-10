# ABM_GUI - Build & Run Instructions

## Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Open browser
http://localhost:3000
```

## Requirements

- **Node.js**: v16 or higher
- **npm**: v7 or higher

Check versions:
```bash
node --version
npm --version
```

## Installation

```bash
cd MicroCpy/ABM_GUI
npm install
```

This installs:
- React 18
- React Flow 11
- Zustand (state management)
- Vite (build tool)
- Lucide React (icons)

## Development

```bash
npm run dev
```

- Opens at `http://localhost:3000`
- Hot module replacement enabled
- Changes auto-reload in browser

## Build for Production

```bash
npm run build
```

- Output: `dist/` folder
- Optimized and minified
- Ready for deployment

## Preview Production Build

```bash
npm run preview
```

## Usage

### 1. Import Workflow
- Click "Import JSON"
- Select `example_workflow.json`
- All 5 stages load automatically

### 2. Edit Workflow
- Switch between stage tabs
- Drag functions from palette
- Connect nodes with arrows
- Double-click to edit parameters

### 3. Export Workflow
- Click "Export JSON"
- Save to file
- Use with MicroC: `python run_microc.py --workflow your_workflow.json`

## File Structure

```
ABM_GUI/
├── src/
│   ├── components/       # React components
│   ├── data/            # Function registry
│   ├── store/           # Zustand state
│   └── App.jsx          # Main app
├── example_workflow.json # Sample workflow
├── package.json         # Dependencies
└── BUILD.md            # This file
```

## Troubleshooting

### Port 3000 already in use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
npm run dev -- --port 3001
```

### Dependencies not installing
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Hot reload not working
- Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
- Restart dev server

## Integration with MicroC

The GUI generates JSON files compatible with MicroC workflow system:

```bash
# Run simulation with workflow
cd ../microc-2.0
python run_microc.py --config tests/jayatilake_experiment/jayatilake_experiment_config.yaml \
                     --workflow path/to/workflow.json
```

## Features

✅ 5 workflow stages (initialization, intracellular, diffusion, intercellular, finalization)  
✅ Drag-and-drop function placement  
✅ Directed arrows showing execution flow  
✅ Parameter editing with type validation  
✅ Function file tracking (Python implementation)  
✅ Import/Export JSON workflows  
✅ Enable/disable functions  
✅ Visual execution order  

## Browser Support

- Chrome/Edge: ✅ Recommended
- Firefox: ✅ Supported
- Safari: ✅ Supported

## Performance

- Handles 50+ nodes per stage
- Smooth pan/zoom
- Real-time updates
- Optimized rendering

