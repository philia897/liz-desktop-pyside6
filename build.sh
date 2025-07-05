#!/bin/bash

# Build and bundle script for Liz-desktop

# Exit on error
set -e

# Store the root directory
ROOT_DIR=$(pwd)

# Install python dependencies
pip install -r requirements.txt

echo "=== Building Rust module ==="
cd bluebird || { echo "Error: bluebird directory not found"; exit 1; }

# Build the Rust module
maturin build --release --strip --interpreter python

# Find the wheel file (newest one)
WHEEL_FILE=$(ls -t target/wheels/bluebird-*.whl | head -1)

if [ -z "$WHEEL_FILE" ]; then
    echo "Error: No wheel file found in target/wheels/"
    exit 1
fi

echo "Found wheel: $WHEEL_FILE"

# Install the wheel
pip install "$WHEEL_FILE" --force-reinstall

# Return to root directory
cd "$ROOT_DIR"

echo "=== Running PyInstaller ==="
pyinstaller \
    --add-data "theme:theme" \
    --add-data "resources:resources" \
    --name Liz-desktop \
    --onefile \
    --windowed \
    --icon "resources\icon_1024.png" \
    --clean \
    main.py

echo "=== Build complete ==="
echo "Executable created at: $ROOT_DIR/dist/Liz-desktop"