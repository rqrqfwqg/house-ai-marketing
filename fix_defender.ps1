# 修复 Windows Defender 误报 leakless.exe 问题
# 需要以管理员身份运行：右键 → 以管理员身份运行 PowerShell，然后执行：
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   & "C:\Users\yan\WorkBuddy\2026-07-05-18-09-42\house-ai\fix_defender.ps1"

Write-Host "=== 修复 Windows Defender 误报 leakless.exe ===" -ForegroundColor Cyan
Write-Host ""

# 1. 添加排除路径
Write-Host "[1/4] 添加 Defender 排除路径..." -ForegroundColor Yellow

$exclusionPaths = @(
    "C:\Users\yan\AppData\Local\Temp\leakless-amd64-adb80298fa6a3af7ced8b1c9b5f18007",
    "C:\Users\yan\.local\bin"
)

foreach ($path in $exclusionPaths) {
    try {
        Add-MpPreference -ExclusionPath $path -ErrorAction Stop
        Write-Host "  [OK] 已排除: $path" -ForegroundColor Green
    } catch {
        Write-Host "  [SKIP] 已存在或失败: $path" -ForegroundColor DarkGray
    }
}

# 2. 添加排除进程
Write-Host "`n[2/4] 添加 Defender 排除进程..." -ForegroundColor Yellow

$exclusionProcesses = @(
    "xiaohongshu-mcp.exe",
    "xiaohongshu-login.exe",
    "leakless.exe"
)

foreach ($proc in $exclusionProcesses) {
    try {
        Add-MpPreference -ExclusionProcess $proc -ErrorAction Stop
        Write-Host "  [OK] 已排除进程: $proc" -ForegroundColor Green
    } catch {
        Write-Host "  [SKIP] 已存在或失败: $proc" -ForegroundColor DarkGray
    }
}

# 3. 恢复被隔离的 leakless.exe（如果存在）
Write-Host "`n[3/4] 检查并恢复被隔离的文件..." -ForegroundColor Yellow

$threats = Get-MpThreatDetection -ErrorAction SilentlyContinue | Where-Object { $_.Resources -like "*leakless*" }
if ($threats) {
    foreach ($threat in $threats) {
        try {
            # 尝试移除威胁记录（会让Defender不再阻止该文件）
            Remove-MpThreat -ErrorAction SilentlyContinue
            Write-Host "  [OK] 已清理威胁记录" -ForegroundColor Green
            break
        } catch {
            Write-Host "  [WARN] 清理失败: $($_.Exception.Message)" -ForegroundColor Orange
        }
    }
} else {
    Write-Host "  [SKIP] 无隔离记录" -ForegroundColor DarkGray
}

# 4. 重启 xiaohongshu-mcp 服务
Write-Host "`n[4/4] 重启 xiaohongshu-mcp 服务..." -ForegroundColor Yellow

$mcpProcess = Get-Process -Name "xiaohongshu-mcp" -ErrorAction SilentlyContinue
if ($mcpProcess) {
    Stop-Process -Name "xiaohongshu-mcp" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "  [OK] 旧进程已停止" -ForegroundColor Green
}

# 重新启动 MCP 服务
$mcpPath = "C:\Users\yan\.local\bin\xiaohongshu-mcp.exe"
if (Test-Path $mcpPath) {
    Start-Process -FilePath $mcpPath -WindowStyle Minimized
    Start-Sleep -Seconds 3

    # 验证服务
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:18060/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] MCP 服务已重启 (端口 18060)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [WARN] MCP 服务启动中，请稍等..." -ForegroundColor Orange
    }
} else {
    Write-Host "  [ERROR] 找不到 $mcpPath" -ForegroundColor Red
}

# 验证结果
Write-Host "`n=== 验证结果 ===" -ForegroundColor Cyan

# 检查排除列表
$exclusions = Get-MpPreference | Select-Object -ExpandProperty ExclusionPath -ErrorAction SilentlyContinue
if ($exclusions) {
    Write-Host "Defender 排除路径:" -ForegroundColor White
    foreach ($ex in $exclusions) {
        Write-Host "  - $ex" -ForegroundColor Gray
    }
}

# 检查 MCP 健康
try {
    $health = Invoke-WebRequest -Uri "http://localhost:18060/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "`nMCP 服务状态: 正常 (HTTP $($health.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "`nMCP 服务状态: 不可用" -ForegroundColor Red
}

Write-Host "`n=== 修复完成 ===" -ForegroundColor Cyan
Write-Host "请重新尝试获取小红书登录二维码" -ForegroundColor White
