#!/usr/bin/env python3
"""
Test to verify that timestamps INSIDE images are updating correctly.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from workflow.functions.debug.debug_dummy_functions import debug_generate_image


def test_timestamp_updates():
    """Test that timestamps inside images update on each call."""
    
    print("=" * 70)
    print("Testing Timestamp Updates INSIDE Images")
    print("=" * 70)
    
    # Setup test context
    test_dir = Path("results/timestamp_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean up old test files
    for f in test_dir.glob("*.png"):
        f.unlink()
    
    context = {
        "current_step": 0,
        "subworkflow_results_dir": test_dir
    }
    
    print("\nGenerating 3 images with 500ms delay between each...")
    print("Each should have a DIFFERENT timestamp displayed inside.\n")
    
    generated_files = []
    
    for i in range(3):
        print(f"[{i+1}/3] Generating image...")
        
        result = debug_generate_image(
            context=context,
            message=f"Timestamp Test {i+1}",
            filename="timestamp_test"
        )
        
        if result:
            # Find the most recently created file
            files = sorted(test_dir.glob("timestamp_test_*.png"), key=lambda p: p.stat().st_mtime)
            if files:
                latest = files[-1]
                generated_files.append(latest)
                print(f"      Created: {latest.name}")
        
        # Wait 500ms to ensure different timestamps
        if i < 2:  # Don't wait after the last one
            time.sleep(0.5)
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print(f"\nGenerated {len(generated_files)} images:")
    for f in generated_files:
        print(f"  - {f.name}")
    
    print(f"\n📁 Images saved to: {test_dir}")
    print("\n🔍 MANUAL VERIFICATION REQUIRED:")
    print("   Please open the images and check that each one shows a")
    print("   DIFFERENT timestamp in the 'Generated:' text box.")
    print("\n   If all 3 images show the SAME timestamp, there's a bug!")
    
    # Extract timestamps from filenames to show they're different
    print("\n📊 Timestamps from filenames (should be different):")
    for f in generated_files:
        # Extract timestamp from filename: timestamp_test_YYYYMMDD_HHMMSS_mmm_step_SSSS.png
        parts = f.stem.split('_')
        if len(parts) >= 5:
            date_part = parts[2]  # YYYYMMDD
            time_part = parts[3]  # HHMMSS
            ms_part = parts[4]    # mmm
            timestamp_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}.{ms_part}"
            print(f"   {f.name}")
            print(f"      → {timestamp_str}")
    
    print("\n" + "=" * 70)
    
    return True


if __name__ == "__main__":
    test_timestamp_updates()

