#!/usr/bin/env python3
"""
Test the units.py fix for Length class conversion issues.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_length_conversions():
    """Test that Length conversions work correctly."""
    
    print("[TOOL] Testing Length Unit Conversions...")
    print("=" * 50)
    
    try:
        from core.units import Length
        
        # Test the problematic case from the error message
        print("[TARGET] Testing the problematic case: 2e-05 m")
        length_m = Length(2e-05, "m")
        print(f"   Input: {length_m}")
        print(f"   Meters: {length_m.meters}")
        print(f"   Micrometers: {length_m.micrometers}")
        
        # Test micrometers input
        print("\n[TARGET] Testing micrometers input: 20 um")
        length_um = Length(20, "um")
        print(f"   Input: {length_um}")
        print(f"   Meters: {length_um.meters}")
        print(f"   Micrometers: {length_um.micrometers}")
        
        # Test that they're equivalent
        print(f"\n[TARGET] Testing equivalence:")
        print(f"   2e-05 m = {length_m.meters} m")
        print(f"   20 um = {length_um.meters} m")
        print(f"   Equal? {abs(length_m.meters - length_um.meters) < 1e-10}")
        
        # Test other units
        print(f"\n[TARGET] Testing other units:")
        
        # Test millimeters
        length_mm = Length(0.02, "mm")
        print(f"   0.02 mm = {length_mm.meters} m = {length_mm.micrometers} um")
        
        # Test um (alternative spelling)
        length_um_alt = Length(20, "um")
        print(f"   20 um = {length_um_alt.meters} m = {length_um_alt.micrometers} um")
        
        # Test micrometer (full word)
        length_micrometer = Length(20, "micrometer")
        print(f"   20 micrometer = {length_micrometer.meters} m = {length_micrometer.micrometers} um")
        
        # Verify all are equivalent
        all_equal = (
            abs(length_m.meters - length_um.meters) < 1e-10 and
            abs(length_m.meters - length_mm.meters) < 1e-10 and
            abs(length_m.meters - length_um_alt.meters) < 1e-10 and
            abs(length_m.meters - length_micrometer.meters) < 1e-10
        )
        
        print(f"\n[+] All representations equal? {all_equal}")
        
        # Test the range check that was failing
        print(f"\n[TARGET] Testing range validation (1-50 um):")
        test_value = length_m.micrometers
        in_range = 1 <= test_value <= 50
        print(f"   {test_value:.1f} um in range [1, 50]? {in_range}")
        
        if all_equal and in_range:
            print(f"\n[SUCCESS] All tests passed! Units conversion is working correctly.")
            return True
        else:
            print(f"\n[!] Some tests failed!")
            return False
            
    except Exception as e:
        print(f"[!] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_length_conversions()
    if success:
        print("\n[TARGET] Units fix successful!")
    else:
        print("\n[!] Units fix failed!")
        sys.exit(1)
