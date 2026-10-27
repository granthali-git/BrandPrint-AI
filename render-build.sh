#!/usr/bin/env bash
# Render Build Script for BrandPrint AI
set -e

echo "==> Upgrading pip..."
python -m pip install --upgrade pip

echo "==> Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "==> Build finished successfully."
