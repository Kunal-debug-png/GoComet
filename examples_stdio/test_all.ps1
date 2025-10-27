# Test All MCP Stdio Servers
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing All MCP Stdio Servers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorCount = 0

# Test SQL Server
Write-Host "[1/5] Testing SQL Server..." -ForegroundColor Yellow
type sql\last_4_weeks.json | python ..\app\mcp\servers\srv_sql_stdio.py 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ SQL Server working" -ForegroundColor Green
} else {
    Write-Host "  ✗ SQL Server failed" -ForegroundColor Red
    $ErrorCount++
}

# Test Pandas Server
Write-Host ""
Write-Host "[2/5] Testing Pandas Server..." -ForegroundColor Yellow
type pandas\head_3.json | python ..\app\mcp\servers\srv_pandas_stdio.py 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Pandas Server working" -ForegroundColor Green
} else {
    Write-Host "  ✗ Pandas Server failed" -ForegroundColor Red
    $ErrorCount++
}

# Test Plotly Server
Write-Host ""
Write-Host "[3/5] Testing Plotly Server..." -ForegroundColor Yellow
python plotly\line_chart.py 2>&1 | Out-Null
if (Test-Path "plotly\line_chart.png") {
    Write-Host "  ✓ Plotly Server working (chart created)" -ForegroundColor Green
} else {
    Write-Host "  ✗ Plotly Server failed (no chart created)" -ForegroundColor Red
    $ErrorCount++
}

# Test Tracking Server
Write-Host ""
Write-Host "[4/5] Testing Tracking Server..." -ForegroundColor Yellow
type tracking\create_new.json | python ..\app\mcp\servers\srv_tracking_stdio.py 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Tracking Server working" -ForegroundColor Green
} else {
    Write-Host "  ✗ Tracking Server failed" -ForegroundColor Red
    $ErrorCount++
}

# Test FileSystem Server
Write-Host ""
Write-Host "[5/5] Testing FileSystem Server..." -ForegroundColor Yellow
type fs\read_csv.json | python ..\app\mcp\servers\srv_fs_stdio.py 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ FileSystem Server working" -ForegroundColor Green
} else {
    Write-Host "  ✗ FileSystem Server failed" -ForegroundColor Red
    $ErrorCount++
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($ErrorCount -eq 0) {
    Write-Host "✓ All 5 servers working!" -ForegroundColor Green
} else {
    Write-Host "✗ $ErrorCount server(s) failed" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
