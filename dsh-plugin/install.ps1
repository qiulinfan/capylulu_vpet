# Install capylulu-pet into the dsh web profile (idempotent).
# 1. copies the package into ~/.dsh/profiles/web/node_modules/
# 2. appends a dsh.client roster row to cordis.patch.yml
# Then restart 'dsh web' (or next launch) to load the pet.
param(
    [string]$ProfileDir = (Join-Path $env:USERPROFILE ".dsh\profiles\web")
)
$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$pkgDir = Join-Path $root "capylulu-pet"
if (-not (Test-Path (Join-Path $pkgDir "lib\client.js"))) {
    throw "lib/client.js missing - run: node dsh-plugin/capylulu-pet/scripts/build-client.mjs"
}
if (-not (Test-Path $ProfileDir)) {
    throw "Profile not found: $ProfileDir"
}

# 1. package into profile node_modules
$target = Join-Path $ProfileDir "node_modules\capylulu-pet"
if (Test-Path $target) { Remove-Item $target -Recurse -Force }
New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
Copy-Item $pkgDir $target -Recurse -Force
Write-Host "copied package -> $target"

# 2. patch cordis.patch.yml (idempotent)
$patchPath = Join-Path $ProfileDir "cordis.patch.yml"
if (-not (Test-Path $patchPath)) { throw "cordis.patch.yml missing: $patchPath" }
$content = Get-Content $patchPath -Raw -Encoding UTF8
if ($content -match "capylulu-pet") {
    Write-Host "cordis.patch.yml already lists capylulu-pet (skipped)"
} else {
    $entry = @"

# CapyLulu desktop pet (dsh plugin): floating shell-overlay pet driven by the
# current session's running state.
- insert:
    - id: capylulu-pet
      name: capylulu-pet
"@
    # Replace a bare flow-style empty list ("[]") so block entries can follow.
    $content = $content -replace '(?m)^\[\]\s*$', ''
    $content = $content.TrimEnd() + [Environment]::NewLine + $entry + [Environment]::NewLine
    Set-Content -Path $patchPath -Value $content -Encoding UTF8
    Write-Host "patched $patchPath"
}

Write-Host ""
Write-Host "Installed. Restart 'dsh web' to load the pet (the overlay pet appears"
Write-Host "bottom-right; click it to wave)."
