param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if ($Clean) {
    Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
}

python -m PyInstaller packaging\boq_auto_production.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "Production launcher build failed."
}

python -m PyInstaller packaging\boq_auto_admin.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "Admin launcher build failed."
}

Write-Host "Build complete. See dist\\BOQ AUTO Production and dist\\BOQ AUTO Admin"
