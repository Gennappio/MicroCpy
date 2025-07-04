@echo off
echo Multi-Test Runner - Running all 16 combinations
echo ================================================

echo.
echo Validating all configurations...
python tests/multitest/test_combination.py all

echo.
echo Starting individual simulations...
echo This may take several minutes...

for /L %%i in (0,1,15) do (
    echo.
    if %%i LSS 10 (
        echo Running combination 0%%i...
        python run_sim.py tests/multitest/config_0%%i.yaml
        if errorlevel 1 (
            echo ERROR: Combination 0%%i failed
        ) else (
            echo SUCCESS: Combination 0%%i completed
        )
    ) else (
        echo Running combination %%i...
        python run_sim.py tests/multitest/config_%%i.yaml
        if errorlevel 1 (
            echo ERROR: Combination %%i failed
        ) else (
            echo SUCCESS: Combination %%i completed
        )
    )
)

echo.
echo ================================================
echo All combinations completed!
echo Results saved in: plots/multitest/combination_XX/
echo.
pause
