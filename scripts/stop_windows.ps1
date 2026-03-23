$ContainerName = "finally"

$existing = docker ps -aq -f "name=^${ContainerName}$" 2>$null
if ($existing) {
    Write-Host "Stopping FinAlly..."
    docker stop $ContainerName | Out-Null
    docker rm $ContainerName | Out-Null
    Write-Host "Stopped. Data volume preserved."
} else {
    Write-Host "FinAlly is not running."
}
