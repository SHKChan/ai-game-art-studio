#!/usr/bin/env bash
# Build the upstream Atelier engine (unmodified). Requires Rust/cargo.
set -euo pipefail
cd "$(dirname "$0")/../upstream/atelier"
if ! cargo build --release --locked -p atelier; then
  echo "Pinned toolchain unavailable? Retrying with installed stable and --ignore-rust-version" >&2
  RUSTUP_TOOLCHAIN=stable cargo build --release --locked --ignore-rust-version -p atelier
fi
./target/release/atelier --version
