#!/bin/bash

# build_windows_on_kali.sh
# Purpose: Build Windows (.exe) and Installer (.exe) on Kali Linux using Wine

# 1. Build the "Raw" EXE using Windows PyInstaller inside Wine
echo "Step 1: Running Windows PyInstaller (via Wine)..."
wine pyinstaller SolunexLab.spec

# 2. Build the Installer using Inno Setup Compiler (ISCC.exe)
# Note: This assumes you have installed Inno Setup via Wine
echo "Step 2: Compiling Installer with Inno Setup (via Wine)..."
# Replace with the actual path where Inno Setup was installed in Wine
# Often it is: ~/.wine/drive_c/Program Files (x86)/Inno Setup 6/ISCC.exe
ISCC_PATH=$(find ~/.wine -name "ISCC.exe" | head -n 1)

if [ -z "$ISCC_PATH" ]; then
    echo "Error: Inno Setup (ISCC.exe) not found in Wine. Please install it."
    exit 1
fi

wine "$ISCC_PATH" installer.iss

echo "--------------------------------------------------------"
echo "Build Complete!"
echo "Final Installer is in: dist_installer/SolunexLabSetup.exe"
echo "--------------------------------------------------------"
