param([ValidateRange(1,65535)][int]$Port = 5173)
$ErrorActionPreference = 'Stop'
$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$applicationRoot = Join-Path $repositoryRoot 'apps\score-workbench'
$viteEntry = Join-Path $applicationRoot 'node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $viteEntry -PathType Leaf)) {
    throw 'Install dependencies: pnpm --dir apps/score-workbench install --frozen-lockfile'
}
$nodeExecutable = (Get-Command node -ErrorAction Stop).Source
Push-Location -LiteralPath $applicationRoot
try {
    & $nodeExecutable $viteEntry --host 127.0.0.1 --port $Port --strictPort
    if ($LASTEXITCODE -ne 0) { throw "Score workbench exited: $LASTEXITCODE" }
} finally {
    Pop-Location
}
