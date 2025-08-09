#!/bin/bash
# Local CI/CD - Run all checks using invoke

set -e  # Exit on first error

echo "========================================="
echo "Running Local CI/CD Checks (via invoke)"
echo "========================================="
echo ""

# Simply delegate to invoke's ci task which runs everything
poetry run invoke ci
