"""Custom setup.py for building dagctl with bytecode-only distribution."""

import os
import py_compile
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPyCompiled(build_py):
    """Custom build command that compiles to bytecode and removes source files."""

    def byte_compile(self, files):
        """Compile Python source files to bytecode."""
        print("Compiling Python files to bytecode...")
        for file in files:
            if file.endswith(".py"):
                try:
                    py_compile.compile(file, cfile=file + "c", doraise=True, optimize=2)
                    print(f"  Compiled: {file} -> {file}c")
                except py_compile.PyCompileError as e:
                    print(f"  Error compiling {file}: {e}")

    def run(self):
        """Run the build process."""
        # Run the standard build
        super().run()

        # Get the build lib directory
        build_lib = Path(self.build_lib)
        
        print(f"\nProcessing build directory: {build_lib}")
        
        # Find all .py files in the build directory
        py_files = list(build_lib.rglob("*.py"))
        
        if not py_files:
            print("No .py files found in build directory")
            return
        
        print(f"Found {len(py_files)} Python source files")
        
        # Compile all .py files to .pyc
        for py_file in py_files:
            try:
                # Compile with optimization level 2 (removes docstrings and assertions)
                pyc_file = py_file.parent / "__pycache__" / f"{py_file.stem}.cpython-{self.get_python_tag()}.opt-2.pyc"
                
                # Ensure __pycache__ directory exists
                pyc_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Compile
                py_compile.compile(
                    str(py_file),
                    cfile=str(pyc_file),
                    doraise=True,
                    optimize=2
                )
                
                print(f"  Compiled: {py_file.name} -> {pyc_file.name}")
                
                # Move .pyc file to same directory as .py file (not in __pycache__)
                target_pyc = py_file.with_suffix(".pyc")
                shutil.move(str(pyc_file), str(target_pyc))
                
                # Remove the .py source file
                py_file.unlink()
                print(f"  Removed source: {py_file.name}")
                
                # Remove __pycache__ directory if empty
                if pyc_file.parent.exists() and not any(pyc_file.parent.iterdir()):
                    pyc_file.parent.rmdir()
                    
            except Exception as e:
                print(f"  Error processing {py_file}: {e}")
        
        print(f"\nBuild complete: {build_lib}")
        print("Source files removed, only bytecode (.pyc) files remain")

    def get_python_tag(self):
        """Get the Python version tag for .pyc files."""
        import sys
        return f"{sys.version_info.major}{sys.version_info.minor}"


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_py": BuildPyCompiled,
        }
    )
