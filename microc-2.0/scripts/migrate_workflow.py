#!/usr/bin/env python3
"""
CLI tool to migrate v1.0 workflows to v2.0 format.

Usage:
    python migrate_workflow.py input.json output.json
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import workflow module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflow.migrate import WorkflowMigrator


def main():
    parser = argparse.ArgumentParser(
        description="Migrate MicroC v1.0 workflow to v2.0 format"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to v1.0 workflow JSON file"
    )
    parser.add_argument(
        "output",
        type=str,
        help="Path where to save v2.0 workflow JSON file"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it exists"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    # Check input file exists
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    # Check output file doesn't exist (unless --force)
    if output_path.exists() and not args.force:
        print(f"Error: Output file already exists: {output_path}")
        print("Use --force to overwrite")
        sys.exit(1)
    
    try:
        # Perform migration
        print(f"Migrating workflow from {input_path} to {output_path}...")
        WorkflowMigrator.migrate_file(str(input_path), str(output_path))
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

