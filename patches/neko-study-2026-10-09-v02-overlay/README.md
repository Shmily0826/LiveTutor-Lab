# N.E.K.O Study Companion v0.2 source overlay

This is a byte-exact snapshot of the selected Study Companion source files at repository revision `ce79f63ba1941b5b17a8e29521ebf0f0906b89e2`. It preserves the ignored LIVE, BRIDGE, and goal-isolated plugin source roots without copying the vendor binary, runtime databases, screenshots, or credentials.

`manifest.json` records each source path, payload path, byte length, and SHA-256. The three `__init__.py` entrypoints and the source-deployment compatibility entrypoints are captured separately because the roots differ. Selected teaching, lifecycle, mute, schema, grading, and UI modules are captured for each root. The payload contains exactly the 77 files listed in the manifest; no unmanifested files remain.

This is a **snapshot overlay**, not a portable diff or a claim about pristine upstream source. Several changed files have no verified preimage in this checkout. The existing fingerprinted partial patch remains the only portable diff for the five context files whose preimages were preserved.

## Verify

From the repository root:

```powershell
node scripts/verify_neko_source_overlay.mjs
```

The verifier checks every manifest payload and its current ignored source file against the same SHA-256 and byte length. It does not change files or load the plugin.

## Restore or apply to one of these exact source roots

Use only against the matching source deployment. Each `sha256` is both the captured payload fingerprint and the expected destination fingerprint at capture time. Before copying, verify every destination file exists and has the recorded fingerprint. If any destination is missing or differs, stop and review it; do not copy over it. This prevents applying the snapshot over a teammate's later edits or private data. After all destination fingerprints match, make a separate backup of the listed files, copy each listed `payload` file to its `source` path, and verify again. The snapshot does not contain pristine preimages, so it cannot safely automate recovery of a modified or missing destination.

The manifest paths are repository-relative. A PowerShell restore can be driven directly from the manifest after review:

```powershell
$overlay = 'patches/neko-study-2026-10-09-v02-overlay'
$manifest = Get-Content "$overlay/manifest.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$role = 'live' # choose live, bridge, or isolated
$backup = "benchmarks/raw/evidence/neko-v02-source-backup-$role"
$backupRoot = Join-Path (Get-Location) $backup
if (Test-Path -LiteralPath $backupRoot) { throw "Backup directory already exists; choose a fresh path: $backupRoot" }
$items = $manifest.files | Where-Object root -eq $role
foreach ($item in $items) {
    $target = Join-Path (Get-Location) $item.source
    if (!(Test-Path -LiteralPath $target -PathType Leaf)) { throw "Destination missing; stop for review: $($item.source)" }
    $currentHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($currentHash -ne $item.sha256) { throw "Destination fingerprint mismatch; stop for review: $($item.source)" }
    $payload = Join-Path (Get-Location) "$overlay/$($item.payload)"
    $payloadHash = (Get-FileHash -LiteralPath $payload -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($payloadHash -ne $item.sha256) { throw "Payload fingerprint mismatch: $($item.payload)" }
}
New-Item -ItemType Directory -Path $backupRoot | Out-Null
foreach ($item in $items) {
    $target = Join-Path (Get-Location) $item.source
    $saved = Join-Path (Get-Location) "$backup/$($item.source)"
    $payload = Join-Path (Get-Location) "$overlay/$($item.payload)"
    New-Item -ItemType Directory -Force -Path (Split-Path $saved) | Out-Null
    Copy-Item -LiteralPath $target -Destination $saved
    Copy-Item -LiteralPath $payload -Destination $target -Force
}
node scripts/verify_neko_source_overlay.mjs
```

This copies source files only. It does not reload or restart N.E.K.O. There is no original hash for every file, so review the target package version and keep the backup before applying the overlay to any other deployment.
