# Publishing dagctl to PyPI

The package ships as a normal source distribution plus a pure-Python wheel. The repository is public under the Apache-2.0 license, so there is no source obfuscation step.

## Prerequisites

```bash
pip install -e ".[dev]"   # includes build and twine
```

Configure `~/.pypirc` with API tokens for PyPI and, optionally, Test PyPI:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-YOUR-PRODUCTION-API-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TEST-API-TOKEN-HERE
```

## Release checklist

1. **Bump the version in both places.** PyPI refuses to re-upload an existing version, so any change to `README.md` or package metadata needs a new version number.
   - `pyproject.toml`: `version = "X.Y.Z"`
   - `dagctl/__init__.py`: `__version__ = "X.Y.Z"`
2. **Build.** The README is embedded in the wheel metadata at build time, so always rebuild after editing it. `make build` deletes `dist/` first, so any previously built artifacts are gone.

   ```bash
   make build      # cleans build/ and dist/, then runs python -m build
   make verify     # twine check dist/*
   ```

3. **Upload to Test PyPI first (optional but recommended for metadata changes).**

   ```bash
   make upload-test
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ dagctl
   ```

   Check that the README renders correctly on the Test PyPI project page.

4. **Upload to PyPI.**

   ```bash
   make upload-prod
   ```

5. **Tag and push.**

   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```

6. **Verify.**

   ```bash
   pip install --upgrade dagctl
   dagctl --version
   ```

## Why the README matters

PyPI renders `README.md` as the project page, and AI assistants use it as their primary description of dagctl. Every version's README is kept forever, so claims in it must be accurate at the time of release.

## Troubleshooting

- **`twine check` fails on the long description:** the README has Markdown that PyPI cannot render. Fix the Markdown rather than switching to reStructuredText.
- **`HTTPError: 400 File already exists`:** the version in `pyproject.toml` was already published. Bump it and rebuild.
- **Stale files in the wheel:** run `make clean` before `make build`. `make build` does this automatically.
