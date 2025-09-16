import subprocess
import sys
import os
from pathlib import Path

def check_dll_dependencies(dll_path):
    """Check DLL dependencies using objdump or dumpbin"""

    print(f"Analyzing: {dll_path}")

    # Try objdump first (from MinGW tools)
    objdump_cmd = "x86_64-w64-mingw32-objdump"
    try:
        result = subprocess.run([objdump_cmd, "-p", dll_path],
                              capture_output=True, text=True, check=True)
        print("\n=== DLL Dependencies ===")
        lines = result.stdout.split('\n')
        in_imports = False
        for line in lines:
            if "DLL Name:" in line:
                print(f"  -> {line.strip()}")
            elif "The Import Tables" in line:
                in_imports = True
            elif in_imports and line.strip().startswith("DLL Name:"):
                print(f"  -> {line.strip()}")

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("objdump not available, trying alternative methods...")

    # Check if file exists and basic info
    if os.path.exists(dll_path):
        size = os.path.getsize(dll_path)
        print(f"\nDLL Size: {size} bytes")
    else:
        print(f"ERROR: {dll_path} not found!")

def check_exports(dll_path):
    """Check exported functions"""
    try:
        result = subprocess.run(["x86_64-w64-mingw32-objdump", "-p", dll_path],
                              capture_output=True, text=True, check=True)
        print("\n=== Exported Functions ===")
        lines = result.stdout.split('\n')
        for line in lines:
            if "[" in line and "]" in line and "(" not in line:
                # This looks like an export entry
                print(f"  {line.strip()}")
    except:
        print("Could not check exports")

if __name__ == "__main__":
    dll_path = "libaudio.dll"
    if len(sys.argv) > 1:
        dll_path = sys.argv[1]

    check_dll_dependencies(dll_path)
    check_exports(dll_path)
