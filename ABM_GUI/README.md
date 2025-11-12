# MicroC Workflow Designer

A visual workflow designer for MicroC cellular simulations. Design, customize, and export simulation workflows without writing code.

## Features

- 🎨 **Visual Workflow Design**: Drag-and-drop interface for building simulation workflows
- 📊 **5 Workflow Stages**: Separate views for initialization, intracellular, diffusion, intercellular, and finalization
- ⚙️ **Parameter Editing**: Edit function parameters with type-safe inputs
- 💾 **JSON Import/Export**: Load and save workflows compatible with MicroC backend
- 🔄 **React Flow Integration**: Professional node-based workflow editor
- 📦 **Function Library**: Pre-built catalog of simulation functions

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install
```

### Development

```bash
# Start development server
npm run dev
```

The application will open at `http://localhost:3000`

### Build for Production

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Usage

### Creating a Workflow

1. **Select a Stage**: Click on one of the 5 stage tabs (Initialization, Intracellular, Diffusion, Intercellular, Finalization)
2. **Add Functions**: Drag functions from the left palette onto the canvas
3. **Connect Functions**: Draw connections between functions to define execution order
4. **Edit Parameters**: Double-click a function node to edit its parameters
5. **Repeat**: Configure all stages as needed

### Importing a Workflow

1. Click **Import JSON** in the header
2. Select a workflow JSON file (e.g., `jaya_workflow.json`)
3. The workflow will be loaded and displayed

### Exporting a Workflow

1. Click **Export JSON** in the header
2. The workflow will be downloaded as a JSON file
3. Use this file with MicroC: `python run_microc.py --sim config.yaml --workflow your_workflow.json`

## Workflow Stages

### 1. Initialization
Functions that run once at the start of the simulation:
- Initialize cell placement
- Initialize cell ages
- Set up initial conditions

### 2. Intracellular
Functions that run every time step for each cell:
- Calculate cell metabolism
- Update metabolic state
- Check division conditions
- Update phenotype
- Age cells
- Check cell death

### 3. Diffusion
Functions related to substance diffusion (runs every N steps):
- Currently uses default diffusion solver
- Custom diffusion functions can be added

### 4. Intercellular
Functions for cell-cell interactions (runs every M steps):
- Select division direction
- Calculate migration probability
- Cell-cell signaling

### 5. Finalization
Functions that run once at the end of the simulation:
- Generate final reports
- Save final statistics
- Post-processing

## JSON Format

The workflow JSON format is compatible with MicroC backend:

```json
{
  "version": "1.0",
  "name": "My Workflow",
  "description": "Description of the workflow",
  "metadata": {
    "author": "Your Name",
    "created": "2025-01-10"
  },
  "stages": {
    "initialization": {
      "enabled": true,
      "functions": [
        {
          "id": "init_1",
          "function_name": "initialize_cell_placement",
          "parameters": {
            "initial_cell_count": 50,
            "placement_pattern": "spheroid"
          },
          "enabled": true,
          "position": { "x": 100, "y": 100 },
          "description": "Place cells in spheroid"
        }
      ],
      "execution_order": ["init_1"]
    }
  }
}
```

## Technology Stack

- **React 18**: UI framework
- **React Flow**: Node-based workflow editor
- **Zustand**: State management
- **Vite**: Build tool and dev server
- **Lucide React**: Icon library

## Project Structure

```
ABM_GUI/
├── src/
│   ├── components/          # React components
│   │   ├── FunctionPalette.jsx
│   │   ├── WorkflowCanvas.jsx
│   │   ├── WorkflowFunctionNode.jsx
│   │   └── ParameterEditor.jsx
│   ├── data/                # Data and configuration
│   │   └── functionRegistry.js
│   ├── store/               # State management
│   │   └── workflowStore.js
│   ├── App.jsx              # Main application
│   ├── main.jsx             # Entry point
│   └── index.css            # Global styles
├── package.json
├── vite.config.js
└── README.md
```

## Integration with MicroC

The GUI generates JSON files that are directly compatible with MicroC:

```bash
# Design workflow in GUI and export as my_workflow.json
# Then run simulation:
cd ../microc-2.0
python run_microc.py --sim config.yaml --workflow my_workflow.json
```

## Contributing

This is part of the MicroCpy project. See the main repository for contribution guidelines.

## License

Part of the MicroCpy project.

