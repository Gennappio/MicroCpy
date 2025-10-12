#!/usr/bin/env python3
"""
Visualization Demo for MicroC Cell State Analysis Tools

This script demonstrates all visualization capabilities of the MicroC analysis tools.
It creates a comprehensive set of plots and visualizations from cell state files.
"""

import subprocess
import sys
from pathlib import Path
import webbrowser
import time

def run_command(cmd, description):
    """Run a command and display its output"""
    print(f"\n{'='*60}")
    print(f"🎨 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Error: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"[!] Command not found: {cmd[0]}")
        return False

def check_requirements():
    """Check if required packages are installed"""
    print("[*] Checking requirements...")
    
    required_packages = ['h5py', 'numpy', 'matplotlib', 'seaborn', 'pandas']
    optional_packages = ['plotly']
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"[+] {package}")
        except ImportError:
            missing_required.append(package)
            print(f"[!] {package} (required)")
    
    for package in optional_packages:
        try:
            __import__(package)
            print(f"[+] {package} (optional)")
        except ImportError:
            missing_optional.append(package)
            print(f"⚠️  {package} (optional - interactive plots disabled)")
    
    if missing_required:
        print(f"\n[!] Missing required packages: {', '.join(missing_required)}")
        print("Install with: pip install " + " ".join(missing_required))
        return False
    
    if missing_optional:
        print(f"\n⚠️  Missing optional packages: {', '.join(missing_optional)}")
        print("Install with: pip install " + " ".join(missing_optional))
    
    return True

def main():
    print("[CELL] MicroC Cell State Visualization Demo")
    print("=" * 80)
    
    # Check requirements
    if not check_requirements():
        print("\n[!] Please install missing requirements first")
        return
    
    # Check if we have the initial state file
    initial_state_file = "initial_state_3D_S.h5"
    if not Path(initial_state_file).exists():
        print(f"[!] Initial state file not found: {initial_state_file}")
        print("Please run MicroC with save_initial_state: true first")
        return
    
    print(f"\n[+] Found initial state file: {initial_state_file}")
    
    # Create output directory
    output_dir = "demo_visualizations"
    Path(output_dir).mkdir(exist_ok=True)
    print(f"[FILE] Output directory: {output_dir}")
    
    # Demo 1: Basic 2D visualization
    success = run_command(
        ["python", "tools/cell_state_visualizer.py", initial_state_file, 
         "--positions-2d", "--output-dir", output_dir],
        "Basic 2D Cell Position Visualization"
    )
    
    if not success:
        print("[!] Basic visualization failed. Check your setup.")
        return
    
    # Demo 2: 3D visualization
    run_command(
        ["python", "tools/cell_state_visualizer.py", initial_state_file,
         "--positions-3d", "--output-dir", output_dir],
        "3D Cell Position Visualization"
    )
    
    # Demo 3: Phenotype analysis
    run_command(
        ["python", "tools/cell_state_visualizer.py", initial_state_file,
         "--phenotypes", "--output-dir", output_dir],
        "Phenotype Distribution Analysis"
    )
    
    # Demo 4: Gene network analysis
    run_command(
        ["python", "tools/cell_state_visualizer.py", initial_state_file,
         "--gene-heatmap", "--output-dir", output_dir],
        "Gene Network Heatmap"
    )
    
    # Demo 5: Fate gene analysis
    run_command(
        ["python", "tools/cell_state_visualizer.py", initial_state_file,
         "--fate-genes", "--output-dir", output_dir],
        "Fate Gene Analysis"
    )
    
    # Demo 6: Age distribution
    run_command(
        ["python", "tools/cell_state_visualizer.py", initial_state_file,
         "--ages", "--output-dir", output_dir],
        "Cell Age Distribution"
    )
    
    # Demo 7: Interactive 3D plot (if plotly available)
    try:
        import plotly
        run_command(
            ["python", "tools/cell_state_visualizer.py", initial_state_file,
             "--interactive-3d", "--output-dir", output_dir],
            "Interactive 3D Visualization (Plotly)"
        )
        interactive_file = Path(output_dir) / f"{Path(initial_state_file).stem}_interactive_3d.html"
        if interactive_file.exists():
            print(f"Domain: Interactive plot created: {interactive_file}")
            print("   You can open this file in your web browser")
    except ImportError:
        print("⚠️  Plotly not available - skipping interactive 3D plot")
    
    # Demo 8: All plots at once
    run_command(
        ["python", "tools/cell_state_visualizer.py", initial_state_file,
         "--all-plots", "--output-dir", f"{output_dir}/complete_analysis"],
        "Complete Visualization Suite"
    )
    
    # Demo 9: Temporal analysis (if multiple files available)
    cell_states_pattern = "results/jayatilake_experiment/cell_states/*.h5"
    from glob import glob
    temporal_files = glob(cell_states_pattern)
    
    if temporal_files:
        run_command(
            ["python", "tools/cell_state_visualizer.py", cell_states_pattern,
             "--temporal", "--output-dir", f"{output_dir}/temporal"],
            "Temporal Evolution Analysis"
        )
    else:
        print("\n⚠️  No temporal files found - skipping temporal analysis")
        print(f"   Pattern searched: {cell_states_pattern}")
    
    # Demo 10: Quick inspection for comparison
    run_command(
        ["python", "tools/quick_inspect.py", initial_state_file],
        "Quick File Inspection (for comparison)"
    )
    
    # Summary
    print(f"\n{'='*80}")
    print("🎉 VISUALIZATION DEMO COMPLETED!")
    print("=" * 80)
    
    # List created files
    output_path = Path(output_dir)
    created_files = list(output_path.rglob("*"))
    image_files = [f for f in created_files if f.suffix.lower() in ['.png', '.jpg', '.jpeg']]
    html_files = [f for f in created_files if f.suffix.lower() == '.html']
    
    print(f"[STATS] Created {len(image_files)} image files:")
    for img_file in sorted(image_files):
        print(f"   Step: {img_file.relative_to(output_path)}")
    
    if html_files:
        print(f"\nDomain: Created {len(html_files)} interactive files:")
        for html_file in sorted(html_files):
            print(f"   [LINK] {html_file.relative_to(output_path)}")
    
    print(f"\n[FILE] All files saved in: {output_dir}")
    print("\n💡 Visualization Types Created:")
    print("   🗺️  2D/3D cell position plots")
    print("   Phenotypes: Phenotype distribution charts")
    print("   [CELL] Gene network activation heatmaps")
    print("   [TARGET] Fate gene analysis plots")
    print("   [STATS] Cell age distribution histograms")
    if html_files:
        print("   Domain: Interactive 3D plots")
    if temporal_files:
        print("   Step: Temporal evolution analysis")
    
    print("\n🚀 Next Steps:")
    print("   1. Open the image files to view static plots")
    if html_files:
        print("   2. Open HTML files in your web browser for interactive plots")
    print("   3. Use the analysis tools with your own cell state files")
    print("   4. Customize plots by modifying the visualization scripts")
    
    # Offer to open the output directory
    try:
        import platform
        if platform.system() == "Windows":
            subprocess.run(["explorer", str(output_path)], check=False)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(output_path)], check=False)
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", str(output_path)], check=False)
        print(f"\n[*] Opened output directory: {output_path}")
    except:
        print(f"\n[*] Please manually open: {output_path}")

if __name__ == "__main__":
    main()
