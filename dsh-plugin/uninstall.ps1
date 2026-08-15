# Uninstall capylulu-pet from the dsh web profile (idempotent).
param(
    [string]$ProfileDir = (Join-Path $env:USERPROFILE ".dsh\profiles\web")
)
$ErrorActionPreference = "Stop"

$patchPath = Join-Path $ProfileDir "cordis.patch.yml"
if (Test-Path $patchPath) {
    $content = Get-Content $patchPath -Raw -Encoding UTF8
    $updated = [regex]::Replace(
        $content,
        "(?ms)^[ \t]*-[ \t]*insert:[\r\n]+([ \t]+-[ \t]*id:[ \t]*capylulu-pet[\r\n]+[ \t]+[^\r\n]*[\r\n]?)+",
        ""
    )
    # fallback: strip a single-line insert entry
    $updated = [regex]::Replace($updated, "(?m)^[ \t]*-[ \t]*id:[ \t]*capylulu-pet[ \t]*$[\r\n]?", "")
    if ($updated -ne $content) {
        Set-Content -Path $patchPath -Value ($updated.TrimEnd() + [Environment]::NewLine) -Encoding UTF8
        Write-Host "removed capylulu-pet entry from $patchPath"
    } else {
        Write-Host "no capylulu-pet entry found in $patchPath"
    }
}

$target = Join-Path $ProfileDir "node_modules\capylulu-pet"
if (Test-Path $target) {
    Remove-Item $target -Recurse -Force
    Write-Host "removed $target"
} else {
    Write-Host "package not installed at $target"
}
Write-Host "Done. Restart 'dsh web' for the pet to disappear."
