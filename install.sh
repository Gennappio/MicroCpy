#!/bin/bash
# OpenCellComms Installation Script for macOS/Linux
# This script sets up the complete development environment

set -e  # Exit on any error

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           OpenCellComms Installation Script                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_status "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_status "Node.js found: $NODE_VERSION"
else
    print_error "Node.js not found. Please install Node.js 18 or higher."
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_status "npm found: $NPM_VERSION"
else
    print_error "npm not found. Please install npm 7 or higher."
    exit 1
fi

echo ""
echo "Creating Python virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    print_status "Virtual environment created: .venv/"
else
    print_warning "Virtual environment already exists: .venv/"
fi

# Activate virtual environment
source .venv/bin/activate
print_status "Virtual environment activated"

echo ""
echo "Installing Python engine..."

# Install the engine package
cd opencellcomms_engine
pip install --upgrade pip > /dev/null 2>&1
pip install -e . > /dev/null 2>&1
print_status "OpenCellComms engine installed"

# Install Flask server dependencies
pip install flask flask-cors > /dev/null 2>&1
print_status "Flask server dependencies installed"

cd ..

echo ""
echo "Installing GUI dependencies..."

# Install GUI dependencies
cd opencellcomms_gui
npm install > /dev/null 2>&1
print_status "GUI dependencies installed"

cd ..

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "To get started:"
echo ""
echo "  1. Activate the virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Run OpenCellComms:"
echo "     ./run.sh"
echo ""
echo "  3. Open http://localhost:3000 in your browser"
echo ""
echo "For more information, see docs/INSTALL.md and docs/USAGE.md"
echo ""

