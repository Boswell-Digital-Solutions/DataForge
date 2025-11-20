#!/bin/bash

# VibeForge Backend Quick Start Script
# This script sets up the entire backend in one go

set -e

echo "🚀 VibeForge Backend Setup"
echo "=========================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $PYTHON_VERSION"

# Check Rust/Cargo
if ! command -v cargo &> /dev/null; then
    echo "❌ Rust not found. Install from https://rustup.rs/"
    exit 1
fi
RUST_VERSION=$(rustc --version | awk '{print $2}')
echo "✓ Rust $RUST_VERSION"

# Check Maturin
if ! command -v maturin &> /dev/null; then
    echo "📦 Installing maturin..."
    cargo install maturin
fi
MATURIN_VERSION=$(maturin --version | awk '{print $2}')
echo "✓ Maturin $MATURIN_VERSION"

echo ""
echo "📁 Creating virtual environment..."
python3 -m venv venv

echo "🔌 Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate

echo ""
echo "🦀 Building Rust extensions (forge_core, forge_prompt, forge_data, forge_eval)..."
echo "   This takes 2-3 minutes on first run..."
maturin develop

echo ""
echo "📦 Installing Python dependencies..."
pip install -e .[dev]

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Start the dev server: uvicorn app.main:app --reload"
echo "  2. Open API docs: http://localhost:8000/docs"
echo "  3. Run tests: pytest tests/ -v"
echo ""
echo "Happy coding! 🎉"
