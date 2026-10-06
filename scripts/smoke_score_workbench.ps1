param([ValidateRange(1,65535)][int]$Port = 5184)
$ErrorActionPreference = 'Stop'
$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$applicationRoot = Join-Path $repositoryRoot 'apps\score-workbench'
$receiptRoot = Join-Path $repositoryRoot 'output\repository-consolidation-2026-10-06'
$nodeExecutable = (Get-Command node -ErrorAction Stop).Source
$viteEntry = Join-Path $applicationRoot 'node_modules\vite\bin\vite.js'
$serverProcess = $null
$receipt = [ordered]@{ port=$Port; host='127.0.0.1'; passed=$false; source_work='work-fd275425506cc192'; requests=@(); cleanup=$null }
try {
    # Launch only our new server, directly through Node; preserve old services.
    $quotedVite = '"' + $viteEntry + '"'
    $serverProcess = Start-Process -FilePath $nodeExecutable -ArgumentList @($quotedVite,'--host','127.0.0.1','--port',"$Port",'--strictPort') -WorkingDirectory $applicationRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $receiptRoot 'smoke-stdout.txt') -RedirectStandardError (Join-Path $receiptRoot 'smoke-stderr.txt')
    $receipt.pid = $serverProcess.Id
    $ready = $false
    for ($readinessAttempt = 0; $readinessAttempt -lt 30; $readinessAttempt++) {
        if ($serverProcess.HasExited) { throw 'Owned smoke server exited before readiness.' }
        try {
            $page = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 2
            if ($page.StatusCode -eq 200) { $ready=$true; break }
        } catch { }
        Start-Sleep -Milliseconds 200
    }
    if (-not $ready) { throw 'Owned smoke server was not ready within the bounded check.' }
    $receipt.requests += @{ path='/'; status=$page.StatusCode; html=$page.Content.Contains('id="root"') }
    $url = "http://127.0.0.1:$Port/api/work/work-fd275425506cc192?phraseLayers=1&motifDiscovery=1"
    $apiStart = [Diagnostics.Stopwatch]::StartNew()
    $workResponse = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 45
    $apiStart.Stop()
    $work = $workResponse.Content | ConvertFrom-Json
    $receipt.requests += @{ path='/api/work/<known-work>?phraseLayers=1&motifDiscovery=1'; status=$workResponse.StatusCode; seconds=$apiStart.Elapsed.TotalSeconds; fields=@($work.PSObject.Properties.Name); response_bytes=$workResponse.RawContentLength }
    if ($workResponse.StatusCode -ne 200 -or -not $work.phraseLayers -or -not $work.motifDiscovery) { throw 'Expected comparison layers are missing from the work response.' }
    $receipt.passed = $true
} catch {
    $receipt.error = $_.Exception.Message
} finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        # We retain the LIVE Process object; no enumeration/termination by name.
        $taskkillExecutable = Join-Path $env:SystemRoot 'System32\taskkill.exe'
        & $taskkillExecutable /PID $serverProcess.Id /T /F | Out-Null
        $cleanupCode = $LASTEXITCODE
        $serverProcess.WaitForExit(5000) | Out-Null
        $receipt.cleanup = @{ owned_pid=$serverProcess.Id; tree_command_exit=$cleanupCode; exited=$serverProcess.HasExited }
        if ($cleanupCode -ne 0 -or -not $serverProcess.HasExited) { $receipt.passed=$false }
    } elseif ($serverProcess) {
        $receipt.cleanup = @{ owned_pid=$serverProcess.Id; already_exited=$true }
    }
    $receiptJson = $receipt | ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText((Join-Path $receiptRoot 'http-smoke.json'), $receiptJson, [Text.UTF8Encoding]::new($false))
    Write-Output $receiptJson
}
if (-not $receipt.passed) { exit 1 }
