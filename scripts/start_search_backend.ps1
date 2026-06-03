$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (-not (Get-Process | Where-Object { $_.ProcessName -like "*Docker Desktop*" })) {
    if (Test-Path $dockerDesktop) {
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
        Write-Host "Starting Docker Desktop..."
    } else {
        Write-Error "Docker Desktop was not found at $dockerDesktop"
    }
}

$deadline = (Get-Date).AddMinutes(2)
do {
    try {
        $version = docker version --format "{{.Server.Version}}" 2>$null
        if ($LASTEXITCODE -eq 0 -and $version) {
            Write-Host "Docker engine is ready: $version"
            break
        }
    } catch {
        Start-Sleep -Seconds 3
    }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

if ((Get-Date) -ge $deadline) {
    Write-Error "Docker engine did not become ready within 2 minutes."
}

docker compose up -d searxng

$healthDeadline = (Get-Date).AddMinutes(1)
do {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/search?q=health%20check&format=json" -TimeoutSec 15
        Write-Host "SearXNG health check HTTP status: $($response.StatusCode)"
        exit 0
    } catch {
        Start-Sleep -Seconds 5
    }
} while ((Get-Date) -lt $healthDeadline)

Write-Error "SearXNG container started, but the HTTP health check did not pass within 1 minute."
