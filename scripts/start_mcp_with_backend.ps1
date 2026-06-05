param(
    [switch]$Api,
    [string]$Uv = "uv",
    [int]$DockerTimeoutSeconds = 180,
    [int]$HealthTimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$cacheDir = Join-Path $projectRoot ".cache"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
$startupLog = Join-Path $cacheDir "mcp-startup.log"
$eventLog = Join-Path $cacheDir "mcp-events.jsonl"

function Write-StartupLog {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("s")
    Add-Content -LiteralPath $startupLog -Value "$timestamp $Message" -Encoding UTF8
}

function Fail-Startup {
    param([string]$Message)
    Write-StartupLog "ERROR $Message"
    [Console]::Error.WriteLine($Message)
    exit 1
}

function Test-DockerEngine {
    try {
        $version = docker version --format "{{.Server.Version}}" 2>$null
        return ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($version))
    } catch {
        return $false
    }
}

Write-StartupLog "Starting LM Studio MCP wrapper."

if (-not (Test-DockerEngine)) {
    $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path -LiteralPath $dockerDesktop) {
        Write-StartupLog "Docker engine is not ready. Starting Docker Desktop."
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
    } else {
        Fail-Startup "Docker Desktop was not found at $dockerDesktop"
    }
}

$dockerDeadline = (Get-Date).AddSeconds($DockerTimeoutSeconds)
while (-not (Test-DockerEngine)) {
    if ((Get-Date) -gt $dockerDeadline) {
        Fail-Startup "Docker engine did not become ready within $DockerTimeoutSeconds seconds. See $startupLog"
    }
    Start-Sleep -Seconds 3
}
Write-StartupLog "Docker engine is ready."

if ($Api) {
    Write-StartupLog "Starting SearXNG plus API/UI containers."
    docker compose --profile api up -d searxng api *>> $startupLog
} else {
    Write-StartupLog "Starting SearXNG container."
    docker compose up -d searxng *>> $startupLog
}
if ($LASTEXITCODE -ne 0) {
    Fail-Startup "docker compose failed with exit code $LASTEXITCODE. See $startupLog"
}

$healthDeadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
$searxngReady = $false
while (-not $searxngReady) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/search?q=health%20check&format=json" -TimeoutSec 15
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            $searxngReady = $true
            Write-StartupLog "SearXNG health check HTTP status: $($response.StatusCode)"
            break
        }
    } catch {
        Write-StartupLog "Waiting for SearXNG health check."
    }
    if ((Get-Date) -gt $healthDeadline) {
        Fail-Startup "SearXNG did not become ready within $HealthTimeoutSeconds seconds. See $startupLog"
    }
    Start-Sleep -Seconds 5
}

if (-not $env:SEARXNG_BASE_URL) {
    $env:SEARXNG_BASE_URL = "http://127.0.0.1:8080"
}
$env:LOCAL_REALTIME_SEARCH_LOG_FILE = $eventLog
Write-StartupLog "Launching MCP server. Event logs: $eventLog"

& $Uv run --extra mcp python scripts/mcp_server.py
exit $LASTEXITCODE
