# Publishing dagctl to PyPI (Bytecode Only)

This document describes how to build and publish dagctl to PyPI with only compiled bytecode (`.pyc` files), without exposing the source code (`.py` files).

## Prerequisites

1. Install required build tools:
```bash
pip install build twine wheel setuptools
```

2. Configure PyPI credentials (see below)

## Build Process

### Option 1: Using Make (Recommended)

```bash
# Show all available commands
make help

# Build and verify for test PyPI
make test-build

# Upload to test PyPI
make upload-test

# Or do everything in one command
make release-test
```

### Option 2: Using the Build Script

```bash
./build_bytecode.sh
```

This script will:
- Clean previous builds
- Build a wheel with bytecode compilation
- Remove all `.py` source files
- Verify no source files remain
- Show the wheel contents

### Option 3: Manual Build

```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info

# Build the wheel
python setup.py bdist_wheel

# Verify contents
unzip -l dist/*.whl | grep -E "\.pyc$|\.py$"
```

## Publishing to PyPI

### Test PyPI (Recommended for first time)

1. Create an account at https://test.pypi.org

2. Generate an API token:
   - Go to https://test.pypi.org/manage/account/token/
   - Create a new API token with scope for the project
   - Save the token securely

3. Configure `.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TEST-API-TOKEN-HERE

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-YOUR-PRODUCTION-API-TOKEN-HERE
```

4. Upload to Test PyPI:
```bash
twine upload --repository testpypi dist/*
```

5. Test installation:
```bash
pip install --index-url https://test.pypi.org/simple/ dagctl
```

### Production PyPI

1. Create an account at https://pypi.org

2. Generate an API token:
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token
   - Save the token securely

3. Upload to production PyPI:
```bash
twine upload dist/*
```

4. Verify installation:
```bash
pip install dagctl
```

## Security Considerations

### What's Protected

✅ **Source Code**: All `.py` files are removed  
✅ **Business Logic**: Compiled to bytecode  
✅ **Comments & Docstrings**: Removed with optimization level 2

### What's NOT Protected

⚠️ **Function Names**: Still visible in bytecode  
⚠️ **Variable Names**: Still visible in bytecode  
⚠️ **Import Statements**: Still visible  
⚠️ **Class Structure**: Still visible  

### Important Notes

1. **Bytecode is not encryption**: Python bytecode can be decompiled, though it won't be as clean as the original source
2. **License matters**: Ensure your license allows for bytecode-only distribution
3. **Debugging is harder**: Users won't see original source in tracebacks
4. **Version compatibility**: `.pyc` files are Python version-specific

## Verification

After building, verify the wheel contains only bytecode:

```bash
# List all Python files in the wheel
unzip -l dist/dagctl-*.whl | grep "\.py\|\.pyc"

# Should only show .pyc files (no .py files)
```

Expected output should show only `.pyc` files in the `dagctl/` directory.

## Troubleshooting

### Problem: Source files still in wheel

**Solution**: Ensure `setup.py` is being used:
```bash
python setup.py bdist_wheel
```

### Problem: Import errors after installation

**Solution**: The `.pyc` files must be in the correct location. They should be directly in the package directory, not in `__pycache__/`.

### Problem: Version mismatch errors

**Solution**: The bytecode is compiled for a specific Python version. Users must use the same major.minor version (e.g., Python 3.11 bytecode won't work with Python 3.10).

## Version Management

When releasing a new version:

1. Update version in `pyproject.toml`:
```toml
[project]
name = "dagctl"
version = "0.2.0"  # Update this
```

2. Clean and rebuild:
```bash
./build_bytecode.sh
```

3. Upload to PyPI:
```bash
twine upload dist/*
```

## Continuous Integration

For automated releases, add to your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Build bytecode wheel
  run: |
    python setup.py bdist_wheel
    
- name: Publish to PyPI
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
  run: |
    twine upload dist/*
```

## Support

For issues with the build process, check:
- Python version compatibility
- setuptools/wheel versions
- Build logs for compilation errors
