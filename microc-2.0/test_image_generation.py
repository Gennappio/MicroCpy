#!/usr/bin/env python3
"""
Test script to verify debug_generate_image creates unique filenames with timestamps.

This script simulates multiple calls to debug_generate_image to ensure
each call creates a unique file that doesn't overwrite previous images.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from workflow.functions.debug.debug_dummy_functions import debug_generate_image


def test_image_generation():
    """Test that multiple image generations create unique files."""
    
    print("=" * 70)
    print("Testing debug_generate_image - Unique Filename Generation")
    print("=" * 70)
    
    # Setup test context
    test_dir = Path("results/test_images")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    context = {
        "current_step": 0,
        "subworkflow_results_dir": test_dir
    }
    
    generated_files = []
    
    # Test 1: Generate multiple images with same step number
    print("\n[TEST 1] Generating 3 images with step=0 (should create 3 unique files)")
    for i in range(3):
        result = debug_generate_image(
            context=context,
            message=f"Test Image {i+1}",
            filename="test_plot"
        )
        
        if result:
            # Find the most recently created file
            files = sorted(test_dir.glob("test_plot_*.png"), key=lambda p: p.stat().st_mtime)
            if files:
                latest = files[-1]
                generated_files.append(latest)
                print(f"  ✓ Generated: {latest.name}")
        
        # Small delay to ensure different timestamps
        time.sleep(0.1)
    
    # Test 2: Generate images with different step numbers
    print("\n[TEST 2] Generating 2 images with different steps (should create 2 unique files)")
    for step in [1, 2]:
        context["current_step"] = step
        result = debug_generate_image(
            context=context,
            message=f"Test Image Step {step}",
            filename="test_plot"
        )
        
        if result:
            files = sorted(test_dir.glob("test_plot_*.png"), key=lambda p: p.stat().st_mtime)
            if files:
                latest = files[-1]
                generated_files.append(latest)
                print(f"  ✓ Generated: {latest.name}")
        
        time.sleep(0.1)
    
    # Verify results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    unique_files = set(generated_files)
    print(f"\nTotal images generated: {len(generated_files)}")
    print(f"Unique files created: {len(unique_files)}")
    
    if len(unique_files) == len(generated_files):
        print("\n✅ SUCCESS: All images have unique filenames!")
        print("   No files were overwritten.")
    else:
        print("\n❌ FAILURE: Some files were overwritten!")
        print(f"   Expected {len(generated_files)} unique files, got {len(unique_files)}")
    
    print("\nGenerated files:")
    for f in sorted(unique_files):
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.1f} KB)")
    
    print(f"\nAll test images saved to: {test_dir}")
    print("\n" + "=" * 70)
    
    return len(unique_files) == len(generated_files)


if __name__ == "__main__":
    success = test_image_generation()
    sys.exit(0 if success else 1)

