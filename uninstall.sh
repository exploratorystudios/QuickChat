#!/bin/bash

# QuickChat Uninstallation Script
# This script removes QuickChat from the system
# With options to preserve or remove user data and history

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
DATA_DIR="$HOME/.local/share/quickchat/data"
CONFIG_DIR="$HOME/.config/QuickChat"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  QuickChat Uninstallation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if QuickChat is installed
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ QuickChat does not appear to be installed${NC}"
    echo "Installation directory not found: $INSTALL_DIR"
    exit 0
fi

echo -e "${YELLOW}This will uninstall QuickChat from your system.${NC}"
echo ""
echo -e "The following will be removed:"
echo -e "  ${RED}✗ Application files${NC} ($INSTALL_DIR)"
echo -e "  ${RED}✗ Launcher script${NC} ($LAUNCHER_PATH)"
echo -e "  ${RED}✗ Desktop entry${NC} ($DESKTOP_FILE)"
echo ""

# Ask about data and history
echo -e "${YELLOW}Data and History Options:${NC}"
echo ""
echo "Choose what to do with QuickChat data and settings:"
echo "  1) Remove everything (data, history, settings, images)"
echo "  2) Keep data intact (preserve chats, images, settings)"
echo ""

read -p "Enter your choice [1 or 2]: " CHOICE

REMOVE_DATA=false
case $CHOICE in
    1)
        REMOVE_DATA=true
        echo -e "${RED}Data deletion mode: ENABLED${NC}"
        echo ""
        ;;
    2)
        REMOVE_DATA=false
        echo -e "${GREEN}Data preservation mode: ENABLED${NC}"
        echo ""
        ;;
    *)
        echo -e "${RED}Invalid choice. Aborting.${NC}"
        exit 1
        ;;
esac

# Final confirmation
echo -e "${YELLOW}Uninstallation Summary:${NC}"
echo "  • Remove application: YES"
if [ "$REMOVE_DATA" = true ]; then
    echo "  • Remove data & history: YES"
    echo "    - Chats will be deleted"
    echo "    - Images will be deleted"
    echo "    - Settings will be reset"
else
    echo "  • Remove data & history: NO"
    echo "    - Chats will be preserved"
    echo "    - Images will be preserved"
    echo "    - Settings will be preserved"
fi
echo ""

read -p "Continue with uninstallation? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ] && [ "$CONFIRM" != "y" ]; then
    echo -e "${YELLOW}Uninstallation cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Uninstalling QuickChat...${NC}"
echo ""

# Kill any running instances
echo -e "${BLUE}Stopping any running instances...${NC}"
pkill -f "quickchat" || true
sleep 1
echo -e "${GREEN}✓ Done${NC}"
echo ""

# Remove launcher script
echo -e "${BLUE}Removing launcher script...${NC}"
if [ -f "$LAUNCHER_PATH" ]; then
    rm -f "$LAUNCHER_PATH"
    echo -e "${GREEN}✓ Launcher removed${NC}"
else
    echo -e "${YELLOW}⚠ Launcher not found${NC}"
fi
echo ""

# Remove desktop entry
echo -e "${BLUE}Removing desktop entry...${NC}"
if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo -e "${GREEN}✓ Desktop entry removed${NC}"
else
    echo -e "${YELLOW}⚠ Desktop entry not found${NC}"
fi
echo ""

# Update desktop database
echo -e "${BLUE}Updating GNOME desktop cache...${NC}"
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications/" 2>/dev/null || true
    echo -e "${GREEN}✓ Desktop cache updated${NC}"
else
    echo -e "${YELLOW}⚠ update-desktop-database not found${NC}"
fi
echo ""

# Remove application files
echo -e "${BLUE}Removing application files...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✓ Application files removed${NC}"
else
    echo -e "${YELLOW}⚠ Application directory not found${NC}"
fi
echo ""

# Handle data removal if requested
if [ "$REMOVE_DATA" = true ]; then
    echo -e "${BLUE}Removing data and history...${NC}"

    if [ -d "$DATA_DIR" ]; then
        rm -rf "$DATA_DIR"
        echo -e "${GREEN}✓ Data directory removed${NC}"
    else
        echo -e "${YELLOW}⚠ Data directory not found${NC}"
    fi

    if [ -d "$CONFIG_DIR" ]; then
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}✓ Configuration directory removed${NC}"
    else
        echo -e "${YELLOW}⚠ Configuration directory not found${NC}"
    fi

    # Try to remove empty parent directory if no other apps using it
    if [ -d "$HOME/.local/share/quickchat" ]; then
        rmdir "$HOME/.local/share/quickchat" 2>/dev/null || true
    fi

    echo ""
else
    echo -e "${YELLOW}Data preservation mode${NC}"
    if [ -d "$DATA_DIR" ]; then
        echo -e "${GREEN}✓ Chats and images preserved at: $DATA_DIR${NC}"
    fi
    if [ -d "$CONFIG_DIR" ]; then
        echo -e "${GREEN}✓ Settings preserved at: $CONFIG_DIR${NC}"
    fi
    echo ""
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Uninstallation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ "$REMOVE_DATA" = false ]; then
    echo -e "Your QuickChat data has been preserved."
    echo -e "To reinstall QuickChat with your existing chats, run:"
    echo -e "  ${BLUE}./install.sh${NC}"
    echo ""
fi
