chcp 65001 > $null
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
Set-Location "C:\Users\Abdulkhakim\Git-Projects\resume"
Write-Host "=== HERMES + OLLAMA HH VISIBLE RUNNER ===" -ForegroundColor Cyan
Write-Host "Target: https://tashkent.hh.uz/vacancies/finansovyy_analitik" -ForegroundColor Yellow
Write-Host "Typing: 2-3 sec/word natural human pacing | Transition pause: 5-12 sec" -ForegroundColor Yellow
$directArgs = @(
    '--mode',
    'browser',
    '--confirm',
    'none',
    '--daily-limit',
    '200',
    '--limit',
    '200',
    '--wave-size',
    '25',
    '--wave-pause',
    '120',
    '--min-delay',
    '5.0',
    '--max-delay',
    '12.0',
    '--word-delay-min',
    '2.0',
    '--word-delay-max',
    '3.0',
    '--start-url',
    'https://tashkent.hh.uz/vacancies/finansovyy_analitik',
    '--target-min-score',
    '50',
    '--harvest-max-pages',
    '25'
)
& python "C:\Users\Abdulkhakim\Git-Projects\resume\scripts\hh_apply.py" @directArgs
