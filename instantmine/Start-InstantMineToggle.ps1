Set-Location -LiteralPath $PSScriptRoot
$py = "C:\Program Files\Python310\python.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = "python"
}
& $py ".\instantmine_toggle.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
