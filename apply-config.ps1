Set-Location -LiteralPath $PSScriptRoot
python .\apply-config.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to apply config."
    exit $LASTEXITCODE
}
Write-Host "Done. Restart No Man's Sky (or reload the save) to use the new values."
