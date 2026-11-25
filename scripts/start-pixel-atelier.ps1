<# Launch the ORIGINAL Pixel Atelier workbench (upstream, unmodified) in Python UTF-8 mode,
   so its Chinese project JSON is always read/written as UTF-8 on GBK / cp936 / cp1252 Windows systems.
   Usage: powershell -ExecutionPolicy Bypass -File .\scripts\start-pixel-atelier.ps1 [-Port 8898] #>
param([int]$Port = 8898)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
Set-Location (Join-Path $root "upstream\pixel-atelier")
Start-Job -ScriptBlock { param($p) Start-Sleep 2; Start-Process "http://127.0.0.1:$p/" } -ArgumentList $Port | Out-Null
& $py -X utf8 bridge\server.py --port $Port
