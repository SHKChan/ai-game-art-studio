<#
  AI Game Art Studio - Windows launcher.
  Usage:  powershell -ExecutionPolicy Bypass -File .\start.ps1 [-Port 8870] [-Workspace D:\Art\ws] [-ComfyUrl http://127.0.0.1:8188] [-NoBrowser]
  First run creates .venv and installs requirements. The studio works without ComfyUI.
#>
param(
  [int]$Port = 8870,
  [string]$Workspace = "",
  [string]$ComfyUrl = "",
  [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# Load .env (KEY=VALUE lines) if present
if (Test-Path ".env") {
  Get-Content ".env" | Where-Object { $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
  }
}
# UTF-8 mode: avoids GBK/cp936/cp1252 encoding errors (Pixel Atelier writes Chinese JSON with default encodings)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
if ($Workspace) { $env:ARTSTUDIO_WORKSPACE = $Workspace }
if ($ComfyUrl) { $env:COMFYUI_URL = $ComfyUrl }

$pyCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $pyCmd = @("py", "-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyCmd = @("python") }
if (-not $pyCmd) { Write-Error "Python 3.10+ not found. Install from https://www.python.org/downloads/ (tick 'Add python.exe to PATH')."; exit 1 }
$pyExe = $pyCmd[0]; $pyArgs = @($pyCmd | Select-Object -Skip 1)
$ver = & $pyExe @pyArgs -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$ver -lt [version]"3.10") { Write-Error "Python $ver found; 3.10 or newer is required."; exit 1 }

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "Creating virtual environment (.venv) with Python $ver ..."
  & $pyExe @pyArgs -m venv .venv
  & .venv\Scripts\python.exe -m pip install --upgrade pip
  & .venv\Scripts\python.exe -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) { Write-Error "Dependency installation failed (see docs/deployment-windows.md for offline wheels)."; exit 1 }
}
$exe = "upstream\atelier\target\release\atelier.exe"
if (-not (Test-Path $exe) -and -not $env:ATELIER_BIN -and -not (Get-Command atelier -ErrorAction SilentlyContinue)) {
  Write-Warning "Atelier binary not found: the Procedural Studio will show Atelier as unavailable. Run .\scripts\build-atelier.ps1 (needs Rust)."
}
if (-not $NoBrowser) { Start-Job -ScriptBlock { param($p) Start-Sleep 2; Start-Process "http://127.0.0.1:$p/" } -ArgumentList $Port | Out-Null }
& .venv\Scripts\python.exe -m artstudio serve --port $Port
