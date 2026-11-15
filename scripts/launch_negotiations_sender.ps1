param(
    [int]$Limit = 50,
    [switch]$AllPages,
    [switch]$DryRun,
    [switch]$FastTyping,
    [switch]$Visible,
    [switch]$LaunchWindow
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# Ensure Ollama is running for dynamic unique letter generation
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
        }
    } else {
        Write-Host "[OK] Ollama is active on 127.0.0.1:11434." -ForegroundColor Green
    }
}

Ensure-OllamaRunning

$pyScript = Join-Path $RepoRoot "scripts\hh_negotiations_chat_sender.py"
$argList = @("--limit", $Limit)
if ($AllPages) { $argList += "--all-pages" }
if ($DryRun) { $argList += "--dry-run" }
if ($FastTyping) { $argList += "--fast-typing" }
if ($Visible) { $argList += "--visible" }

if ($LaunchWindow) {
    $runnerScript = Join-Path $RepoRoot "data\run_negotiations_chat.ps1"
    $argLines = ($argList | ForEach-Object { "    '{0}'" -f $_ }) -join ",`n"
    $scriptContent = @"
chcp 65001 > `$null
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
`$env:PYTHONUTF8 = '1'
Set-Location "$RepoRoot"
Write-Host "=== HERMES: CHAT COVER LETTER SENDER (NEGOTIATIONS) ===" -ForegroundColor Cyan
Write-Host "Target: https://tashkent.hh.uz/applicant/negotiations | Limit: $Limit" -ForegroundColor Yellow
`$directArgs = @(
$argLines
)
& python "$pyScript" @directArgs
"@
    Set-Content -Path $runnerScript -Value $scriptContent -Encoding UTF8
    if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
        Write-Host "[OK] Opening visible Windows Terminal window for Hermes Chat Sender..." -ForegroundColor Green
        Start-Process -FilePath "wt.exe" -ArgumentList "-w -1 -d `"$RepoRoot`" powershell.exe -NoExit -ExecutionPolicy Bypass -File `"$runnerScript`""
    } else {
        Write-Host "[OK] Opening visible PowerShell window for Hermes Chat Sender..." -ForegroundColor Green
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "start", "`"Hermes Chat Sender`"", "powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$runnerScript`""
    }
} else {
    chcp 65001 > $null
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $env:PYTHONUTF8 = "1"
    Set-Location $RepoRoot
    Write-Host "=== HERMES: CHAT COVER LETTER SENDER (NEGOTIATIONS) ===" -ForegroundColor Cyan
    & python $pyScript @argList
}
