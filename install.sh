#!/bin/bash
# PyGPT Enhanced - Install Script
# Installs Avatar RPM plugin + MCP Memory Server

set -e

COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_RED='\033[0;31m'
NC='\033[0m'

echo -e "${COLOR_BLUE}"
echo "  ____        ____ ____ _____   _____       _"
echo " |  _ \ _   _/ ___|  _ \_   _| | ____|_ __ | |__   __ _ _ __   ___ ___  __| |"
echo " | |_) | | | | |  | |_) || |   |  _| | '_ \| '_ \ / _' | '_ \ / __/ _ \/ _' |"
echo " |  __/| |_| | |__|  __/ | |   | |___| | | | | | | (_| | | | | (_|  __/ (_| |"
echo " |_|    \__, |\____|_|    |_|   |_____|_| |_|_| |_|\__,_|_| |_|\___\___|\__,_|"
echo "        |___/"
echo -e "${NC}"
echo -e "${COLOR_GREEN}Avatar RPM + MCP Memory Cloud for PyGPT${NC}"
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${COLOR_RED}Python3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${COLOR_GREEN}Python $PY_VERSION detected${NC}"

# 2. Install MCP Memory Server deps
echo -e "\n${COLOR_YELLOW}Installing MCP Memory Server dependencies...${NC}"
pip3 install firebase-admin sentence-transformers numpy textblob

# 3. Install Avatar RPM deps
echo -e "\n${COLOR_YELLOW}Installing Avatar RPM dependencies...${NC}"
pip3 install textblob numpy

# 4. Copy plugins to PyGPT
PYGPT_PLUGIN_DIR="src/pygpt_net/plugin"

if [ -d "$PYGPT_PLUGIN_DIR" ]; then
    echo -e "\n${COLOR_YELLOW}Copying plugins to PyGPT...${NC}"
    cp -r src/pygpt_net/plugin/avatar_rpm "$PYGPT_PLUGIN_DIR/"
    cp -r src/pygpt_net/plugin/mcp_memory "$PYGPT_PLUGIN_DIR/"
    echo -e "${COLOR_GREEN}Plugins installed!${NC}"
else
    echo -e "${COLOR_YELLOW}PyGPT directory not found at $PYGPT_PLUGIN_DIR"
    echo -e "Copy plugins manually from src/pygpt_net/plugin/ to your PyGPT installation${NC}"
fi

# 5. Config example
echo -e "\n${COLOR_YELLOW}Creating config from example...${NC}"
if [ ! -f "mcp-memory-server/config.json" ]; then
    cp mcp-memory-server/config.example.json mcp-memory-server/config.json
    echo -e "${COLOR_GREEN}Config created at mcp-memory-server/config.json${NC}"
    echo -e "${COLOR_YELLOW}Edit it with your Firebase credentials!${NC}"
fi

echo -e "\n${COLOR_GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Create Firebase project at https://console.firebase.google.com"
echo "  2. Download service account JSON"
echo "  3. Edit mcp-memory-server/config.json"
echo "  4. Create RPM avatar at https://demo.readyplayer.me/avatar"
echo "  5. Open PyGPT > Plugins > Enable 'Avatar RPM' + 'Memory Cloud'"
echo ""
