#!/usr/bin/env python3
"""
Cell State Analyzer Tool for MicroC 2.0

This tool analyzes and displays the contents of cell state and initial state files
created by the MicroC 3D Initial State System.

Features:
- Display file metadata and structure
- Show cell population statistics
- Analyze gene network states
- Export data to various formats
- Compare multiple files
- Visualize cell distributions

Usage:
    python cell_state_analyzer.py <file_path> [options]
    python cell_state_analyzer.py --help
"""

import argparse
import h5py
import numpy as np
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import sys

class CellStateAnalyzer:
    """Analyzer for MicroC cell state files"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.metadata = {}
        self.cell_data = {}
        self.gene_data = {}
        self.metabolic_data = {}
        
        self._load_file()
    
    def _load_file(self):
        """Load data from HDF5 file"""
        print(f"[*] Loading file: {self.file_path}")
        
        with h5py.File(self.file_path, 'r') as f:
            # Load metadata
            if 'metadata' in f:
                meta_group = f['metadata']
                for key in meta_group.attrs.keys():
                    value = meta_group.attrs[key]
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    self.metadata[key] = value
            
            # Load cell data
            if 'cells' in f:
                cells_group = f['cells']
                self.cell_data = {
                    'ids': [s.decode('utf-8') for s in cells_group['ids'][:]],
                    'positions': cells_group['positions'][:],
                    'phenotypes': [s.decode('utf-8') for s in cells_group['phenotypes'][:]],
                    'ages': cells_group['ages'][:],
                    'division_counts': cells_group['division_counts'][:],
                    'tq_wait_times': cells_group['tq_wait_times'][:]
                }
            
            # Load gene states
            if 'gene_states' in f:
                gene_group = f['gene_states']
                self.gene_data = {
                    'gene_names': [s.decode('utf-8') for s in gene_group['gene_names'][:]],
                    'states': gene_group['states'][:]
                }
            
            # Load metabolic states
            if 'metabolic_states' in f:
                metab_group = f['metabolic_states']
                self.metabolic_data = {
                    'metabolite_names': [s.decode('utf-8') for s in metab_group['metabolite_names'][:]],
                    'values': metab_group['values'][:]
                }
        
        print(f"[+] File loaded successfully")
    
    def display_summary(self):
        """Display file summary"""
        print("\n" + "="*60)
        print("[STATS] CELL STATE FILE SUMMARY")
        print("="*60)
        
        # File info
        print(f"[FILE] File: {self.file_path.name}")
        print(f"Size: Size: {self.file_path.stat().st_size / 1024:.1f} KB")
        
        # Metadata
        if self.metadata:
            print(f"\n[INFO] Metadata:")
            for key, value in self.metadata.items():
                if key == 'domain_info':
                    try:
                        domain = json.loads(value)
                        print(f"   {key}: {domain['dimensions']}D, {domain['nx']}x{domain['ny']}x{domain.get('nz', 1)}")
                    except:
                        print(f"   {key}: {value}")
                else:
                    print(f"   {key}: {value}")
        
        # Cell statistics
        if self.cell_data:
            cell_count = len(self.cell_data['ids'])
            print(f"\n[CELL] Cell Data:")
            print(f"   Cell count: {cell_count}")
            print(f"   Position dimensions: {self.cell_data['positions'].shape[1]}D")
            print(f"   Age range: {self.cell_data['ages'].min():.1f} - {self.cell_data['ages'].max():.1f}")
            print(f"   Division count range: {self.cell_data['division_counts'].min()} - {self.cell_data['division_counts'].max()}")
            
            # Phenotype distribution
            phenotypes, counts = np.unique(self.cell_data['phenotypes'], return_counts=True)
            print(f"   Phenotype distribution:")
            for phenotype, count in zip(phenotypes, counts):
                percentage = count / cell_count * 100
                print(f"     {phenotype}: {count} ({percentage:.1f}%)")
        
        # Gene network statistics
        if self.gene_data:
            gene_count = len(self.gene_data['gene_names'])
            cell_count = self.gene_data['states'].shape[0]
            print(f"\n[CELL] Gene Network Data:")
            print(f"   Gene count: {gene_count}")
            print(f"   States matrix: {cell_count} cells x {gene_count} genes")
            
            # Gene activation statistics
            activation_rates = self.gene_data['states'].mean(axis=0)
            print(f"   Average activation rate: {activation_rates.mean():.3f}")
            
            # Most/least active genes
            gene_names = self.gene_data['gene_names']
            sorted_indices = np.argsort(activation_rates)
            
            print(f"   Most active genes:")
            for i in sorted_indices[-5:]:
                print(f"     {gene_names[i]}: {activation_rates[i]:.3f}")
            
            print(f"   Least active genes:")
            for i in sorted_indices[:5]:
                print(f"     {gene_names[i]}: {activation_rates[i]:.3f}")
        
        # Metabolic data
        if self.metabolic_data:
            metabolite_count = len(self.metabolic_data['metabolite_names'])
            print(f"\n[METAB] Metabolic Data:")
            print(f"   Metabolite count: {metabolite_count}")
            print(f"   Values matrix: {self.metabolic_data['values'].shape[0]} cells x {metabolite_count} metabolites")
    
    def display_detailed_cells(self, max_cells: int = 10):
        """Display detailed information for first N cells"""
        if not self.cell_data:
            print("[!] No cell data available")
            return
        
        print(f"\n[INFO] DETAILED CELL INFORMATION (first {max_cells} cells)")
        print("-" * 80)
        
        cell_count = min(max_cells, len(self.cell_data['ids']))
        
        for i in range(cell_count):
            print(f"\n[CELL] Cell {i+1}:")
            print(f"   ID: {self.cell_data['ids'][i]}")
            print(f"   Position: {tuple(self.cell_data['positions'][i])}")
            print(f"   Phenotype: {self.cell_data['phenotypes'][i]}")
            print(f"   Age: {self.cell_data['ages'][i]:.2f}")
            print(f"   Division count: {self.cell_data['division_counts'][i]}")
            print(f"   TQ wait time: {self.cell_data['tq_wait_times'][i]:.2f}")
            
            # Show gene states for this cell
            if self.gene_data:
                active_genes = []
                for j, gene_name in enumerate(self.gene_data['gene_names']):
                    if self.gene_data['states'][i, j]:
                        active_genes.append(gene_name)
                
                print(f"   Active genes ({len(active_genes)}): {', '.join(active_genes[:10])}")
                if len(active_genes) > 10:
                    print(f"     ... and {len(active_genes) - 10} more")
    
    def display_gene_analysis(self):
        """Display detailed gene network analysis"""
        if not self.gene_data:
            print("[!] No gene network data available")
            return
        
        print(f"\n[CELL] GENE NETWORK ANALYSIS")
        print("-" * 60)
        
        gene_names = self.gene_data['gene_names']
        states_matrix = self.gene_data['states']
        cell_count, gene_count = states_matrix.shape
        
        print(f"[STATS] Network size: {cell_count} cells x {gene_count} genes")
        
        # Activation statistics
        activation_rates = states_matrix.mean(axis=0)
        print(f"[STATS] Overall activation rate: {activation_rates.mean():.3f}")
        
        # Key fate genes analysis
        fate_genes = ['Proliferation', 'Apoptosis', 'Growth_Arrest', 'Necrosis']
        print(f"\n[TARGET] Fate Gene Analysis:")
        for fate_gene in fate_genes:
            if fate_gene in gene_names:
                gene_idx = gene_names.index(fate_gene)
                activation_rate = activation_rates[gene_idx]
                active_count = int(states_matrix[:, gene_idx].sum())
                print(f"   {fate_gene}: {active_count}/{cell_count} cells ({activation_rate:.3f})")
        
        # Input genes analysis
        input_genes = ['Oxygen_supply', 'Glucose_supply', 'MCT1_stimulus']
        print(f"\n[INPUT] Input Gene Analysis:")
        for input_gene in input_genes:
            if input_gene in gene_names:
                gene_idx = gene_names.index(input_gene)
                activation_rate = activation_rates[gene_idx]
                active_count = int(states_matrix[:, gene_idx].sum())
                print(f"   {input_gene}: {active_count}/{cell_count} cells ({activation_rate:.3f})")
        
        # Gene correlation analysis
        print(f"\n[LINK] Gene Correlation Analysis (top 5 pairs):")
        correlations = []
        for i in range(gene_count):
            for j in range(i+1, gene_count):
                corr = np.corrcoef(states_matrix[:, i], states_matrix[:, j])[0, 1]
                if not np.isnan(corr):
                    correlations.append((corr, gene_names[i], gene_names[j]))
        
        correlations.sort(reverse=True)
        for corr, gene1, gene2 in correlations[:5]:
            print(f"   {gene1} <-> {gene2}: {corr:.3f}")
    
    def export_to_csv(self, output_dir: str = "exports"):
        """Export data to CSV files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        base_name = self.file_path.stem
        
        print(f"\n[SAVE] Exporting data to CSV files...")
        
        # Export cell data
        if self.cell_data:
            cell_df = pd.DataFrame({
                'id': self.cell_data['ids'],
                'x': self.cell_data['positions'][:, 0],
                'y': self.cell_data['positions'][:, 1],
                'z': self.cell_data['positions'][:, 2] if self.cell_data['positions'].shape[1] > 2 else 0,
                'phenotype': self.cell_data['phenotypes'],
                'age': self.cell_data['ages'],
                'division_count': self.cell_data['division_counts'],
                'tq_wait_time': self.cell_data['tq_wait_times']
            })
            
            cell_file = output_path / f"{base_name}_cells.csv"
            cell_df.to_csv(cell_file, index=False)
            print(f"   [+] Cell data: {cell_file}")
        
        # Export gene states
        if self.gene_data:
            gene_df = pd.DataFrame(
                self.gene_data['states'],
                columns=self.gene_data['gene_names'],
                index=self.cell_data['ids'] if self.cell_data else None
            )
            
            gene_file = output_path / f"{base_name}_gene_states.csv"
            gene_df.to_csv(gene_file)
            print(f"   [+] Gene states: {gene_file}")
        
        # Export metabolic states
        if self.metabolic_data:
            metab_df = pd.DataFrame(
                self.metabolic_data['values'],
                columns=self.metabolic_data['metabolite_names'],
                index=self.cell_data['ids'] if self.cell_data else None
            )
            
            metab_file = output_path / f"{base_name}_metabolic_states.csv"
            metab_df.to_csv(metab_file)
            print(f"   [+] Metabolic states: {metab_file}")
        
        print(f"[+] Export completed to {output_path}")
    
    def export_summary_json(self, output_file: str = None):
        """Export summary statistics to JSON"""
        if output_file is None:
            output_file = f"{self.file_path.stem}_summary.json"
        
        # Convert metadata to JSON-serializable format
        json_metadata = {}
        for key, value in self.metadata.items():
            if isinstance(value, (np.integer, np.int64)):
                json_metadata[key] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                json_metadata[key] = float(value)
            else:
                json_metadata[key] = str(value)

        summary = {
            'file_info': {
                'name': str(self.file_path.name),
                'size_kb': float(self.file_path.stat().st_size / 1024),
                'analysis_timestamp': datetime.now().isoformat()
            },
            'metadata': json_metadata,
            'cell_statistics': {},
            'gene_statistics': {},
            'metabolic_statistics': {}
        }
        
        # Cell statistics
        if self.cell_data:
            cell_count = len(self.cell_data['ids'])
            phenotypes, counts = np.unique(self.cell_data['phenotypes'], return_counts=True)
            
            summary['cell_statistics'] = {
                'total_cells': int(cell_count),
                'position_dimensions': int(self.cell_data['positions'].shape[1]),
                'age_range': [float(self.cell_data['ages'].min()), float(self.cell_data['ages'].max())],
                'division_count_range': [int(self.cell_data['division_counts'].min()), int(self.cell_data['division_counts'].max())],
                'phenotype_distribution': {str(p): int(c) for p, c in zip(phenotypes, counts)}
            }
        
        # Gene statistics
        if self.gene_data:
            activation_rates = self.gene_data['states'].mean(axis=0)
            summary['gene_statistics'] = {
                'total_genes': int(len(self.gene_data['gene_names'])),
                'average_activation_rate': float(activation_rates.mean()),
                'gene_activation_rates': {
                    str(gene): float(rate) for gene, rate in zip(self.gene_data['gene_names'], activation_rates)
                }
            }
        
        # Metabolic statistics
        if self.metabolic_data:
            summary['metabolic_statistics'] = {
                'total_metabolites': int(len(self.metabolic_data['metabolite_names'])),
                'metabolite_names': [str(name) for name in self.metabolic_data['metabolite_names']]
            }
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"[SAVE] Summary exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze MicroC cell state and initial state files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cell_state_analyzer.py initial_state_3D_S.h5
  python cell_state_analyzer.py cell_state_step000001.h5 --detailed-cells 5
  python cell_state_analyzer.py initial_state.h5 --export-csv --export-json
  python cell_state_analyzer.py state.h5 --gene-analysis --no-summary
        """
    )
    
    parser.add_argument('file_path', help='Path to the cell state HDF5 file')
    parser.add_argument('--detailed-cells', type=int, default=0, 
                       help='Show detailed info for N cells (default: 0)')
    parser.add_argument('--gene-analysis', action='store_true',
                       help='Show detailed gene network analysis')
    parser.add_argument('--export-csv', action='store_true',
                       help='Export data to CSV files')
    parser.add_argument('--export-json', action='store_true',
                       help='Export summary to JSON file')
    parser.add_argument('--no-summary', action='store_true',
                       help='Skip summary display')
    parser.add_argument('--output-dir', default='exports',
                       help='Output directory for exports (default: exports)')
    
    args = parser.parse_args()
    
    try:
        # Create analyzer
        analyzer = CellStateAnalyzer(args.file_path)
        
        # Display summary
        if not args.no_summary:
            analyzer.display_summary()
        
        # Show detailed cells
        if args.detailed_cells > 0:
            analyzer.display_detailed_cells(args.detailed_cells)
        
        # Show gene analysis
        if args.gene_analysis:
            analyzer.display_gene_analysis()
        
        # Export data
        if args.export_csv:
            analyzer.export_to_csv(args.output_dir)
        
        if args.export_json:
            analyzer.export_summary_json()
        
        print(f"\n[+] Analysis completed successfully!")
        
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
