#!/bin/bash
# Build vclipboard .deb package. Run from anywhere.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
dpkg-deb --root-owner-group --build vclipboard-deb vclipboard_1.0.0_all.deb
echo "Built: $(pwd)/vclipboard_1.0.0_all.deb"
echo ""
echo "Uninstall (if already installed):  sudo dpkg -r vclipboard"
echo "Install (starts automatically):     sudo dpkg -i vclipboard_1.0.0_all.deb"
echo "Or with deps:                       sudo apt install -y ./vclipboard_1.0.0_all.deb"
