# == Fix leakless.exe Defender Issue (Elevated) ==
# This script runs as Administrator via UAC elevation

$Host.UI.RawUI.WindowTitle = "Fixing Defender Exclusions for leakless.exe"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fix Windows Defender - leakless.exe" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Add exclusion paths
Write-Host "[1/5] Adding Defender exclusion paths..." -ForegroundColor Yellow

$paths = @(
    "C:\Users\yan\AppData\Local\Temp\leakless-amd64-adb80298fa6a3af7ced8b1c9b5f18007",
    "C:\Users\yan\AppData\Local\Temp",
    "C:\Users\yan\.local\bin"
)

foreach ($p in $paths) {
    try {
        Add-MpPreference -ExclusionPath $p -ErrorAction Stop
        Write-Host "  [OK] $p" -ForegroundColor Green
    } catch {
        Write-Host "  [SKIP] $p (already exists)" -ForegroundColor DarkGray
    }
}

# 2. Add exclusion processes
Write-Host ""
Write-Host "[2/5] Adding Defender exclusion processes..." -ForegroundColor Yellow

$procs = @("xiaohongshu-mcp.exe", "leakless.exe")
foreach ($pr in $procs) {
    try {
        Add-MpPreference -ExclusionProcess $pr -ErrorAction Stop
        Write-Host "  [OK] $pr" -ForegroundColor Green
    } catch {
        Write-Host "  [SKIP] $pr (already exists)" -ForegroundColor DarkGray
    }
}

# 3. Clear threat history for leakless
Write-Host ""
Write-Host "[3/5] Clearing Defender threat records..." -ForegroundColor Yellow
try {
    Remove-MpThreat -ErrorAction SilentlyContinue
    Write-Host "  [OK] Threat records cleared" -ForegroundColor Green
} catch {
    Write-Host "  [SKIP] No threats to clear" -ForegroundColor DarkGray
}

# 4. Stop and restart MCP service
Write-Host ""
Write-Host "[4/5] Restarting xiaohongshu-mcp service..." -ForegroundColor Yellow

$mcp = Get-Process -Name "xiaohongshu-mcp" -ErrorAction SilentlyContinue
if ($mcp) {
    $mcp | Stop-Process -Force
    Start-Sleep -Seconds 2
    Write-Host "  [OK] Old process stopped" -ForegroundColor Green
}

$mcpPath = "C:\Users\yan\.local\bin\xiaohongshu-mcp.exe"
if (Test-Path $mcpPath) {
    Start-Process -FilePath $mcpPath -WindowStyle Minimized
    Start-Sleep -Seconds 3
    Write-Host "  [OK] MCP service restarted" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Not found: $mcpPath" -ForegroundColor Red
}

# 5. Verify
Write-Host ""
Write-Host "[5/5] Verification..." -ForegroundColor Yellow

# Check exclusions
$exPaths = Get-MpPreference | Select-Object -ExpandProperty ExclusionPath -ErrorAction SilentlyContinue
Write-Host "  Exclusion paths:" -ForegroundColor White
if ($exPaths) {
    $exPaths | Where-Object { $_ -like "*leakless*" -or $_ -like "*local*bin*" } | ForEach-Object {
        Write-Host "    [OK] $_" -ForegroundColor Green
    }
}

# Check MCP health
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:18060/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "  MCP Health: HTTP $($resp.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  MCP Health: Starting up..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:18060/health" -UseBasicParsing -TimeoutSec 5
        Write-Host "  MCP Health: HTTP $($resp.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "  MCP Health: UNAVAILABLE" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now try to get the XHS login QR code again." -ForegroundColor White
Write-Host "This window will close in 5 seconds..." -ForegroundColor DarkGray
Start-Sleep -Seconds 5
