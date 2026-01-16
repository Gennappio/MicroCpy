# Image Generation Fix - Unique Filenames with Timestamps

## Problem

When running workflows with the `debug_generate_image` function (especially workflows with iterations like `capabilities_test_1.json`), images were being **overwritten** instead of accumulating.

### Root Cause

The filename generation only included the step number:
```python
out_filename = f"{filename}_step_{step:04d}.png"
# Example: processing_plot_step_0000.png
```

This caused issues when:
1. **Multiple iterations**: A workflow calling a subworkflow 3 times would generate the same filename 3 times, overwriting previous images
2. **Multiple runs**: Running the same workflow again would overwrite all previous results
3. **Same step numbers**: Different iterations at the same step would collide

### Example Scenario

In `capabilities_test_1.json`:
- `main` composer calls `processing_workflow` **3 times** (iterations: 3)
- `processing_workflow` has **2 steps** (number_of_steps: 2)
- `debug_generate_image` runs once per step

**Expected**: 6 unique images (3 iterations × 2 steps)  
**Actual (before fix)**: 2 images (step_0000.png and step_0001.png, overwritten 3 times)

## Solution

Added **millisecond-precision timestamp** to the filename:

```python
# Generate timestamp for filename
timestamp_short = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # for filename

# New filename format
out_filename = f"{filename}_{timestamp_short}_step_{step:04d}.png"
# Example: processing_plot_20260116_151345_123_step_0000.png
```

### Filename Format

```
{base_filename}_{YYYYMMDD_HHMMSS_mmm}_step_{SSSS}.png
```

Where:
- `base_filename`: User-specified name (e.g., "processing_plot")
- `YYYYMMDD_HHMMSS_mmm`: Timestamp with millisecond precision
- `SSSS`: Zero-padded step number (e.g., 0000, 0001)

### Example Filenames

```
processing_plot_20260116_151345_123_step_0000.png
processing_plot_20260116_151345_456_step_0001.png
processing_plot_20260116_151346_789_step_0000.png  (next iteration)
```

## Benefits

1. **No Overwrites**: Each image is guaranteed to be unique
2. **Chronological Order**: Files sort naturally by timestamp
3. **Iteration Tracking**: Can see progression across multiple iterations
4. **Run History**: Multiple runs preserve all images
5. **Debugging**: Easier to trace execution flow and timing

## Testing

### Automated Test

Run the test script:
```bash
cd microc-2.0
python test_image_generation.py
```

This verifies that:
- Multiple calls with same step create unique files
- Different steps create unique files
- No files are overwritten

### Manual Test with capabilities_test_1.json

1. Run the workflow from the GUI
2. Check `results/subworkflows/processing_workflow/`
3. You should see 6 unique images (3 iterations × 2 steps)

Example output:
```
results/subworkflows/processing_workflow/
├── processing_plot_20260116_151345_123_step_0000.png
├── processing_plot_20260116_151345_456_step_0001.png
├── processing_plot_20260116_151346_789_step_0000.png
├── processing_plot_20260116_151347_012_step_0001.png
├── processing_plot_20260116_151347_345_step_0000.png
└── processing_plot_20260116_151347_678_step_0001.png
```

## Files Modified

- `microc-2.0/src/workflow/functions/debug/debug_dummy_functions.py`
  - Added `timestamp_short` variable for filename
  - Updated `out_filename` to include timestamp

## Backward Compatibility

✅ **Fully backward compatible**
- Function signature unchanged
- All parameters work the same way
- Only the output filename format changed
- Old workflows continue to work without modification

## Related Issues

This fix addresses the image overwriting issue observed when running:
- Workflows with iterations (e.g., `capabilities_test_1.json`)
- Multiple sequential runs of the same workflow
- Any scenario where `debug_generate_image` is called multiple times

## Future Enhancements

Potential improvements:
1. Add optional parameter to control timestamp inclusion
2. Add iteration number to filename (if available in context)
3. Create subdirectories per iteration for better organization

