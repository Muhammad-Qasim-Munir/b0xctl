#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="/usr/local/bin/b0xctl"

# Remove old symlink if it exists
if [ -L "$TARGET" ]; then
    sudo rm "$TARGET"
fi

# Create new symlink
sudo ln -s "$SCRIPT_DIR/b0xctl.py" "$TARGET"
sudo chmod +x "$SCRIPT_DIR/b0xctl.py"

# Copy config.json to the same directory as the symlink
sudo cp "$SCRIPT_DIR/config.json" "/usr/local/bin/config.json"

echo "b0xctl installed to /usr/local/bin/b0xctl" 