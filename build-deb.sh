#!/bin/bash
# Build vclipboard .deb package.
# Run this script from anywhere; it will always build the .deb
# IN THIS FOLDER (the folder that contains DEBIAN/, usr/, etc/).
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

dpkg-deb --root-owner-group --build . vclipboard_1.0.0_all.deb

echo "Built: $(pwd)/vclipboard_1.0.0_all.deb"
echo ""
echo "Uninstall (if already installed):  sudo dpkg -r vclipboard"
echo "Install (starts automatically):     sudo dpkg -i ./vclipboard_1.0.0_all.deb"
echo "Or with deps:                       sudo apt install -y ./vclipboard_1.0.0_all.deb"
