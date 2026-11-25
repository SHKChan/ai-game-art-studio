<# Build the upstream Atelier engine (unmodified) on Windows. Requires Rust (https://rustup.rs).
   Upstream pins Rust 1.98 in rust-toolchain.toml; rustup installs it automatically when online. #>
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\upstream\atelier")
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) { Write-Error "cargo not found. Install Rust from https://rustup.rs then re-run."; exit 1 }
cargo build --release --locked -p atelier
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Build with the pinned toolchain failed. If the 1.98 toolchain cannot be downloaded, try: `$env:RUSTUP_TOOLCHAIN='stable'; cargo build --release --locked --ignore-rust-version -p atelier"
  exit $LASTEXITCODE
}
& .\target\release\atelier.exe --version
Write-Host "Atelier built: upstream\atelier\target\release\atelier.exe (auto-detected by the studio)."
