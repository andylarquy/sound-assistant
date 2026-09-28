# Convenience wrapper so you don't have to remember the full invocation.
# Usage: .\run.ps1 (from agents/windows), or override any default:
#   .\run.ps1 -SinkHost 192.168.1.4 -Name "Andres' PC"

param(
    [string]$Server = "http://192.168.1.4:8000",
    [string]$SinkHost = "192.168.1.4",
    [int]$SinkPort = 4953,
    [int]$SyncPort = 1704,
    [string]$StreamName = "pc",
    [string]$Name = "Andres' PC"
)

$python = Join-Path $PSScriptRoot "..\..\.venv\Scripts\python.exe"

& $python (Join-Path $PSScriptRoot "main.py") `
    --server $Server `
    --sink-host $SinkHost `
    --sink-port $SinkPort `
    --sync-port $SyncPort `
    --stream-name $StreamName `
    --name $Name
