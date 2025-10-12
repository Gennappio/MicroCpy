# PowerShell script to run all 16 combinations
Write-Host "Multi-Test Runner - Running all 16 combinations" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

Write-Host ""
Write-Host "Validating all configurations..." -ForegroundColor Yellow
python tests/multitest/test_combination.py all

if ($LASTEXITCODE -ne 0) {
    Write-Host "Configuration validation failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting individual simulations..." -ForegroundColor Yellow
Write-Host "This may take several minutes..." -ForegroundColor Yellow

$successful = 0
$failed = 0
$startTime = Get-Date

for ($i = 0; $i -le 15; $i++) {
    $configFile = "tests/multitest/config_{0:D2}.yaml" -f $i
    
    Write-Host ""
    Write-Host "Running combination $($i.ToString('D2'))..." -ForegroundColor Cyan
    
    $simStart = Get-Date
    python run_sim.py $configFile
    $simEnd = Get-Date
    $duration = ($simEnd - $simStart).TotalSeconds
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS: Combination $($i.ToString('D2')) completed in $([math]::Round($duration, 1)) seconds" -ForegroundColor Green
        $successful++
    } else {
        Write-Host "ERROR: Combination $($i.ToString('D2')) failed after $([math]::Round($duration, 1)) seconds" -ForegroundColor Red
        $failed++
    }
}

$endTime = Get-Date
$totalDuration = ($endTime - $startTime).TotalMinutes

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "All combinations completed!" -ForegroundColor Green
Write-Host "Total time: $([math]::Round($totalDuration, 1)) minutes" -ForegroundColor Yellow
Write-Host "Successful: $successful/16" -ForegroundColor Green
Write-Host "Failed: $failed/16" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host "Results saved in: plots/multitest/combination_XX/" -ForegroundColor Yellow
Write-Host ""

if ($failed -eq 0) {
    Write-Host "🎉 All simulations completed successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️ Some simulations failed. Check the output above for details." -ForegroundColor Yellow
}

Read-Host "Press Enter to continue"
