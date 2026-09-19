Set-Location -LiteralPath $PSScriptRoot
python .\apply-config.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build no-overheat mod."
    exit $LASTEXITCODE
}
Write-Host "Done. Restart No Man's Sky; you should see the mod warning screen before loading a save."
