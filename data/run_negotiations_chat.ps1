chcp 65001 > $null
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
Set-Location "C:\Users\Abdulkhakim\Git-Projects\resume"
Write-Host "=== HERMES: CHAT COVER LETTER SENDER (NEGOTIATIONS) ===" -ForegroundColor Cyan
Write-Host "Target: https://tashkent.hh.uz/applicant/negotiations | Limit: 50" -ForegroundColor Yellow
$directArgs = @(
    '--limit',
    '50',
    '--dry-run'
)
& python "C:\Users\Abdulkhakim\Git-Projects\resume\scripts\hh_negotiations_chat_sender.py" @directArgs
