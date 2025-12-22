#!/bin/bash
# Build script for creating bytecode-only distribution of dagctl

set -e

echo "================================================"
echo "Building dagctl with bytecode-only distribution"
echo "================================================"
echo ""

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info
echo "  ✓ Cleaned"
echo ""

# Build the wheel distribution
echo "Building wheel with bytecode compilation..."
python setup.py bdist_wheel
echo "  ✓ Built wheel"
echo ""

# Show the contents of the wheel
echo "Wheel contents:"
echo "---------------"
unzip -l dist/*.whl | grep -E "\\.pyc$|\\.py$" || echo "No Python files found"
echo ""

# Verify no .py files in the wheel (only .pyc)
echo "Verifying source files removed..."
if unzip -l dist/*.whl | grep -E "\\.py$" | grep -v "__init__.py" | grep -v "setup.py"; then
    echo "  ⚠️  WARNING: .py source files found in wheel!"
    exit 1
else
    echo "  ✓ No source files found (only bytecode)"
fi
echo ""

echo "Build complete!"
echo "Wheel file: $(ls dist/*.whl)"
echo ""
echo "To test the package locally:"
echo "  pip install dist/$(ls dist | grep .whl)"
echo ""
echo "To upload to TestPyPI:"
echo "  twine upload --repository testpypi dist/*"
echo ""
echo "To upload to PyPI:"
echo "  twine upload dist/*"
