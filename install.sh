#!/bin/bash

# QuickChat Installation Script
# This script installs QuickChat from source to ~/.local/share/quickchat/app
# Compatible with systems that have never seen QuickChat before

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="$HOME/.local/share/quickchat/app"
LAUNCHER_PATH="$HOME/.local/bin/quickchat"
DESKTOP_FILE="$HOME/.local/share/applications/quickchat.desktop"
ICON_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/icon.png"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  QuickChat Installation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if source files exist
if [ ! -d "$PROJECT_DIR/src" ]; then
    echo -e "${RED}Error: Source files not found in $PROJECT_DIR/src${NC}"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/main.py" ]; then
    echo -e "${RED}Error: main.py not found in $PROJECT_DIR${NC}"
    exit 1
fi

if [ ! -f "$ICON_SOURCE" ]; then
    echo -e "${RED}Error: icon.png not found in $PROJECT_DIR${NC}"
    exit 1
fi

# Check Python3 and pip
echo -e "${BLUE}Checking Python and pip...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed${NC}"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Found $PYTHON_VERSION${NC}"
echo ""

# Create installation directory
echo -e "${BLUE}Setting up installation directory...${NC}"
mkdir -p "$INSTALL_DIR"
echo -e "${GREEN}✓ Installation directory ready${NC}"
echo ""

# Check if already installed
if [ -d "$INSTALL_DIR/venv" ]; then
    echo -e "${BLUE}Detected existing QuickChat installation${NC}"
    echo -e "${YELLOW}Updating existing installation...${NC}"
    IS_UPDATE=true
else
    echo -e "${BLUE}Fresh installation detected${NC}"
    IS_UPDATE=false
fi
echo ""

# Copy source files (update existing or fresh install)
echo -e "${BLUE}Copying/updating source files...${NC}"
rm -rf "$INSTALL_DIR/src"  # Remove old src to ensure clean update
cp -r "$PROJECT_DIR/src" "$INSTALL_DIR/"
cp "$PROJECT_DIR/main.py" "$INSTALL_DIR/"
cp "$PROJECT_DIR/config" "$INSTALL_DIR/" 2>/dev/null || true
cp "$ICON_SOURCE" "$INSTALL_DIR/icon.png"
cp "$PROJECT_DIR/requirements.txt" "$INSTALL_DIR/"
echo -e "${GREEN}✓ Source files updated${NC}"
echo ""

# Create or update virtual environment
if [ "$IS_UPDATE" = true ]; then
    echo -e "${BLUE}Updating Python virtual environment...${NC}"
    # Virtual environment already exists, just skip creation
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
else
    echo -e "${BLUE}Creating Python virtual environment...${NC}"
    python3 -m venv "$INSTALL_DIR/venv"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo ""

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓ pip upgraded${NC}"
echo ""

# Install dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠ requirements.txt not found, skipping dependency installation${NC}"
fi
echo ""

# Create launcher script
echo -e "${BLUE}Creating launcher script...${NC}"
mkdir -p "$HOME/.local/bin"
cat > "$LAUNCHER_PATH" << 'EOF'
#!/bin/bash
# QuickChat Launcher

QUICKCHAT_DIR="${HOME}/.local/share/quickchat/app"
PYTHON_BIN="${QUICKCHAT_DIR}/venv/bin/python3"

# Check if directory exists
if [ ! -d "$QUICKCHAT_DIR" ]; then
    echo "Error: QuickChat installation not found at $QUICKCHAT_DIR"
    exit 1
fi

# Check if python exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Error: Python executable not found at $PYTHON_BIN"
    exit 1
fi

# Change to app directory and run
cd "$QUICKCHAT_DIR"
exec "$PYTHON_BIN" main.py "$@"
EOF
chmod +x "$LAUNCHER_PATH"
echo -e "${GREEN}✓ Launcher script created at $LAUNCHER_PATH${NC}"
echo ""

# Create desktop entry
echo -e "${BLUE}Creating GNOME desktop entry...${NC}"
mkdir -p "$HOME/.local/share/applications"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=QuickChat
Comment=Chat interface for Ollama models
Exec=$LAUNCHER_PATH
Icon=$INSTALL_DIR/icon.png
Terminal=false
Categories=Utility;Chat;
StartupWMClass=QuickChat
EOF
echo -e "${GREEN}✓ Desktop entry created${NC}"
echo ""

# Update desktop database
echo -e "${BLUE}Updating GNOME desktop cache...${NC}"
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications/" 2>/dev/null || true
    echo -e "${GREEN}✓ Desktop cache updated${NC}"
else
    echo -e "${YELLOW}⚠ update-desktop-database not found, skipping cache update${NC}"
fi
echo ""

# Create data directory for app
echo -e "${BLUE}Setting up data directories...${NC}"
mkdir -p "$HOME/.local/share/quickchat/data"
mkdir -p "$HOME/.local/share/quickchat/data/images"
echo -e "${GREEN}✓ Data directories created${NC}"
echo ""

# Verify installation
echo -e "${BLUE}Verifying installation...${NC}"
if [ -f "$LAUNCHER_PATH" ] && [ -f "$INSTALL_DIR/main.py" ] && [ -d "$INSTALL_DIR/venv" ]; then
    echo -e "${GREEN}✓ Installation verified${NC}"
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "You can now launch QuickChat by running:"
    echo -e "${BLUE}  quickchat${NC}"
    echo ""
    echo -e "Or find it in your applications menu as 'QuickChat'"
    echo ""
else
    echo -e "${RED}✗ Installation verification failed${NC}"
    exit 1
fi
