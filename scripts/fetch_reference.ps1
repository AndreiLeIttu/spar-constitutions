$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$referencePath = Join-Path $projectRoot 'references/scir'
if (-not (Test-Path $referencePath)) {
    git clone https://github.com/idiap/SciR.git $referencePath
    if ($LASTEXITCODE -ne 0) { throw 'SciR clone failed' }
}
git -C $referencePath checkout --detach d6985141e3b9b6a02bf596034935fbd485ffadf3
if ($LASTEXITCODE -ne 0) { throw 'SciR checkout failed' }
