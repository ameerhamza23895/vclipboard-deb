# V Clipboard (.deb package)

This folder contains the **Debian/Ubuntu/Kali package** for V Clipboard.

## Install from GitHub – step by step

Assuming this folder is the root of your GitHub repo:

1. **Clone the repo**

   ```bash
   git clone https://github.com/YOUR_USER/YOUR_REPO.git
   cd YOUR_REPO/vclipboard-deb
   ```

2. **Build the .deb**

   ```bash
   bash build-deb.sh
   ```

   This creates `vclipboard_1.0.0_all.deb` **in this same folder**.

3. **Install the package (recommended)**

   ```bash
   sudo apt install -y ./vclipboard_1.0.0_all.deb
   ```

   - Installs `vclipboard` system‑wide.
   - Sets up autostart so it runs on login.
   - After install, you can press **Win+V** or **Ctrl+Alt+V** to open the clipboard.

4. **Uninstall / reinstall**

   ```bash
   # Uninstall
   sudo dpkg -r vclipboard

   # Reinstall
   sudo apt install -y ./vclipboard_1.0.0_all.deb
   ```

For full documentation, features, and usage, see the main `README.md` in the source repo.
