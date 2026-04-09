#!/bin/bash

# setup_kali_build.sh
# Purpose: Configure Kali Linux to build Windows (.exe) apps using Wine

echo "--------------------------------------------------------"
echo "Kali-to-Windows Setup: Solunex Lab Scientist"
echo "--------------------------------------------------------"

# 1. Update and install Wine + 32-bit support (Required for Kali)
echo "Step 1: Enabling 32-bit support and installing Wine..."
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install -y wine wine64 wine32:i386

# 2. Download Windows Python (Version 3.11 recommended for stability with PyInstaller)
PYTHON_EXE="python-3.11.9-amd64.exe"
if [ ! -f "$PYTHON_EXE" ]; then
    echo "Step 2: Downloading Windows Python Installer..."
    wget https://www.python.org/ftp/python/3.11.9/$PYTHON_EXE
else
    echo "Windows Python installer already exists."
fi

# 3. Install Python inside Wine
echo "Step 3: Launching Windows Python Installer (Wine)..."
echo "IMPORTANT: In the installer window, check 'Add Python to PATH' and click 'Install Now'."

# Force 64-bit wine prefix to avoid architecture mismatches
export WINEARCH=win64
wine $PYTHON_EXE
if [ $? -ne 0 ]; then
    echo "Error: Wine failed to execute the installer."
    exit 1
fi

# 4. Install Windows-native Python dependencies
echo "Step 4: Installing libraries inside Wine..."
wine python -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "Error: Failed to upgrade pip."
    exit 1
fi
wine python -m pip install pyinstaller PySide6 requests
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies."
    exit 1
fi

echo "--------------------------------------------------------"
echo "Setup Complete!"
echo "You can now run: ./build_windows_on_kali.sh"
echo "--------------------------------------------------------"
