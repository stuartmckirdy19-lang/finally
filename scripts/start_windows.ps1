$ErrorActionPreference = "Stop"

$ImageName = "finally"
$ContainerName = "finally"
$ProjectDir = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectDir

try {
    # Stop existing container if running
    $existing = docker ps -aq -f "name=^${ContainerName}$" 2>$null
    if ($existing) {
        Write-Host "Stopping existing container..."
        docker stop $ContainerName | Out-Null
        docker rm $ContainerName | Out-Null
    }

    # Build image if --build flag passed or image doesn't exist
    $needsBuild = $false
    if ($args -contains "--build") {
        $needsBuild = $true
    } else {
        docker image inspect $ImageName 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $needsBuild = $true
        }
    }

    if ($needsBuild) {
        Write-Host "Building Docker image..."
        docker build -t $ImageName .
    }

    # Run container
    docker run -d `
        --name $ContainerName `
        -v finally-data:/app/db `
        -p 8000:8000 `
        --env-file .env `
        $ImageName

    Write-Host ""
    Write-Host "FinAlly is running at http://localhost:8000"
    Write-Host "To stop: .\scripts\stop_windows.ps1"

    # Open browser
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8000"
}
finally {
    Pop-Location
}
