param(
    [ValidateSet("browser", "api", "assist")]
    [string]$Mode = "browser",

    [ValidateSet("none", "batch", "each")]
    [string]$Confirm = "none",

    [int]$DailyLimit = 200,
    [int]$WaveSize = 25,
    [int]$WavePause = 120,
    [string]$StartUrl = "https://tashkent.hh.uz/vacancies/finansovyy_analitik",
    [int]$TargetMinScore = 50,
    [int]$HarvestMaxPages = 25,
    [switch]$TargetOnly,
    [switch]$LaunchWindow,
    [switch]$WaitWindow
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Ensure-OllamaRunning {
    $ollamaReady = $false
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
        $ollamaReady = $true
    } catch {
        $ollamaReady = $false
    }
    if (-not $ollamaReady) {
        $ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
        if (Test-Path $ollamaExe) {
            Write-Host "[INIT] Starting Ollama server on 127.0.0.1:11434..." -ForegroundColor Cyan
            Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Minimized
            Start-Sleep -Seconds 3
        } else {
            Write-Warning "ollama.exe not found at $ollamaExe"
        }
    } else {
        Write-Host "[OK] Ollama listening on port 11434." -ForegroundColor Green
    }
}

Ensure-OllamaRunning

$pyScript = Join-Path $RepoRoot "scripts\hh_apply.py"
$argList = @(
    "--mode", $Mode,
    "--confirm", $Confirm,
    "--daily-limit", $DailyLimit,
    "--limit", $DailyLimit,
    "--wave-size", $WaveSize,
    "--wave-pause", $WavePause,
    "--min-delay", "5.0",
    "--max-delay", "12.0",
    "--word-delay-min", "2.0",
    "--word-delay-max", "3.0"
)
if ($StartUrl -and $StartUrl.Trim().Length -gt 0) {
    $argList += @("--start-url", $StartUrl.Trim(), "--target-min-score", $TargetMinScore, "--harvest-max-pages", $HarvestMaxPages)
}
if ($TargetOnly) {
    $argList += "--target-only"
}

if ($LaunchWindow) {
    $runnerScript = Join-Path $RepoRoot "data\run_visible.ps1"
    $argLines = ($argList | ForEach-Object { "    '{0}'" -f $_ }) -join ",`n"
    $scriptContent = @"
chcp 65001 > `$null
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
`$env:PYTHONUTF8 = '1'
Set-Location "$RepoRoot"
Write-Host "=== HERMES + OLLAMA HH VISIBLE RUNNER ===" -ForegroundColor Cyan
Write-Host "Mode: $Mode | Confirm: $Confirm | Daily Limit: $DailyLimit | Wave: $WaveSize" -ForegroundColor Yellow
`$directArgs = @(
$argLines
)
& python "$pyScript" @directArgs
"@
    Set-Content -Path $runnerScript -Value $scriptContent -Encoding UTF8
    if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
        Write-Host "[OK] Opening visible Windows Terminal window ($Mode / confirm=$Confirm)..." -ForegroundColor Green
        Start-Process -FilePath "wt.exe" -ArgumentList "-w -1 -d `"$RepoRoot`" powershell.exe -NoExit -ExecutionPolicy Bypass -File `"$runnerScript`""
    } else {
        Write-Host "[OK] Opening visible PowerShell window ($Mode / confirm=$Confirm)..." -ForegroundColor Green
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "start", "`"Hermes HH Runner`"", "powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$runnerScript`""
    }
} else {
    chcp 65001 > $null
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $env:PYTHONUTF8 = "1"
    Set-Location $RepoRoot
    Write-Host "=== HERMES + OLLAMA HH VISIBLE RUNNER ===" -ForegroundColor Cyan
    & python $pyScript @argList
}
