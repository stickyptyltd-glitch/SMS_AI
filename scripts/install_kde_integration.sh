#!/bin/bash
"""
KDE Integration Installation Script
Installs SynapseFlow AI as a native KDE application
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DESKTOP_FILE="$PROJECT_DIR/desktop/synapseflow-ai.desktop"

echo "🐧 Installing SynapseFlow AI KDE Integration"
echo "============================================"

# Check if running on KDE
if [ "$XDG_CURRENT_DESKTOP" != "KDE" ] && [ -z "$KDE_SESSION_VERSION" ]; then
    echo "⚠️  This script is designed for KDE Plasma desktop environment"
    echo "   You can still install, but some features may not work properly"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install dependencies
echo "📦 Installing dependencies..."

# Check for PyQt5 (for system tray)
if ! python3 -c "import PyQt5" 2>/dev/null; then
    echo "Installing PyQt5 for system tray integration..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y python3-pyqt5
    elif command -v pacman &> /dev/null; then
        sudo pacman -S python-pyqt5
    elif command -v dnf &> /dev/null; then
        sudo dnf install python3-qt5
    elif command -v zypper &> /dev/null; then
        sudo zypper install python3-qt5
    else
        echo "⚠️  Please install PyQt5 manually for system tray support"
    fi
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/48x48/apps"

# Create application icon (simple placeholder)
echo "🖼️  Creating application icon..."
cat > "$PROJECT_DIR/desktop/synapseflow-ai.svg" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg width="48" height="48" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Background circle -->
  <circle cx="24" cy="24" r="22" fill="url(#gradient)" stroke="#4a5568" stroke-width="2"/>

  <!-- AI Brain symbol -->
  <g transform="translate(12, 12)">
    <!-- Neural network nodes -->
    <circle cx="6" cy="6" r="2" fill="#ffffff"/>
    <circle cx="18" cy="6" r="2" fill="#ffffff"/>
    <circle cx="12" cy="12" r="2" fill="#ffffff"/>
    <circle cx="6" cy="18" r="2" fill="#ffffff"/>
    <circle cx="18" cy="18" r="2" fill="#ffffff"/>

    <!-- Neural network connections -->
    <line x1="6" y1="6" x2="12" y2="12" stroke="#ffffff" stroke-width="1.5" opacity="0.7"/>
    <line x1="18" y1="6" x2="12" y2="12" stroke="#ffffff" stroke-width="1.5" opacity="0.7"/>
    <line x1="12" y1="12" x2="6" y2="18" stroke="#ffffff" stroke-width="1.5" opacity="0.7"/>
    <line x1="12" y1="12" x2="18" y2="18" stroke="#ffffff" stroke-width="1.5" opacity="0.7"/>
    <line x1="6" y1="6" x2="18" y2="18" stroke="#ffffff" stroke-width="1" opacity="0.5"/>
    <line x1="18" y1="6" x2="6" y2="18" stroke="#ffffff" stroke-width="1" opacity="0.5"/>
  </g>

  <!-- SMS symbol -->
  <rect x="8" y="28" width="32" height="16" rx="3" fill="none" stroke="#ffffff" stroke-width="2"/>
  <line x1="12" y1="34" x2="36" y2="34" stroke="#ffffff" stroke-width="2"/>
  <line x1="12" y1="38" x2="28" y2="38" stroke="#ffffff" stroke-width="2"/>
</svg>
EOF

# Convert SVG to PNG if possible
if command -v convert &> /dev/null; then
    convert "$PROJECT_DIR/desktop/synapseflow-ai.svg" "$PROJECT_DIR/desktop/synapseflow-ai.png"
elif command -v inkscape &> /dev/null; then
    inkscape "$PROJECT_DIR/desktop/synapseflow-ai.svg" --export-png="$PROJECT_DIR/desktop/synapseflow-ai.png" --export-width=48 --export-height=48
else
    echo "⚠️  Install ImageMagick or Inkscape to generate PNG icon"
    # Create a simple placeholder
    cp "$PROJECT_DIR/desktop/synapseflow-ai.svg" "$PROJECT_DIR/desktop/synapseflow-ai.png"
fi

# Update desktop file with correct paths
echo "⚙️  Updating desktop file paths..."
sed -i "s|Icon=.*|Icon=$PROJECT_DIR/desktop/synapseflow-ai.png|" "$DESKTOP_FILE"
sed -i "s|Exec=.*|Exec=$PROJECT_DIR/scripts/launch_kde.sh|" "$DESKTOP_FILE"
sed -i "s|Path=.*|Path=$PROJECT_DIR|" "$DESKTOP_FILE"

# Install desktop file
echo "📋 Installing desktop file..."
cp "$DESKTOP_FILE" "$HOME/.local/share/applications/"

# Install icon
if [ -f "$PROJECT_DIR/desktop/synapseflow-ai.png" ]; then
    cp "$PROJECT_DIR/desktop/synapseflow-ai.png" "$HOME/.local/share/icons/hicolor/48x48/apps/"
fi

# Update desktop database
echo "🔄 Updating desktop database..."
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications"
fi

if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor"
fi

# Create KDE service menu (right-click context menu)
echo "📋 Creating KDE service menus..."
mkdir -p "$HOME/.local/share/kservices5/ServiceMenus"

cat > "$HOME/.local/share/kservices5/ServiceMenus/synapseflow-ai.desktop" << EOF
[Desktop Entry]
Type=Service
ServiceTypes=text/plain
MimeType=text/plain
Actions=sendToSynapseFlow;

[Desktop Action sendToSynapseFlow]
Name=Send to SynapseFlow AI
Icon=synapseflow-ai
Exec=$PROJECT_DIR/scripts/send_to_synapseflow.sh %u
EOF

# Create the send script
cat > "$PROJECT_DIR/scripts/send_to_synapseflow.sh" << 'EOF'
#!/bin/bash
# Script to send text files to SynapseFlow AI for processing

FILE="$1"

if [ ! -f "$FILE" ]; then
    kdialog --error "File not found: $FILE"
    exit 1
fi

# Read file content
CONTENT=$(cat "$FILE")

if [ -z "$CONTENT" ]; then
    kdialog --error "File is empty or cannot be read"
    exit 1
fi

# Get contact name from user
CONTACT=$(kdialog --inputbox "Enter contact name for this message:")

if [ -z "$CONTACT" ]; then
    exit 0
fi

# Send to SynapseFlow AI
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
source .venv/bin/activate 2>/dev/null || true

# Make API call
RESPONSE=$(python3 -c "
import requests
import json
import sys

try:
    response = requests.post('http://localhost:8081/reply',
        json={
            'incoming': '''$CONTENT''',
            'contact': '$CONTACT',
            'platform': 'file'
        },
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        print(data.get('draft', 'No response generated'))
    else:
        print(f'Error: HTTP {response.status_code}')

except Exception as e:
    print(f'Error: {e}')
")

# Show response
kdialog --textbox <(echo "$RESPONSE") 600 400
EOF

chmod +x "$PROJECT_DIR/scripts/send_to_synapseflow.sh"

echo "✅ KDE Integration installed successfully!"
echo ""
echo "🎉 SynapseFlow AI is now integrated with KDE Plasma!"
echo ""
echo "You can now:"
echo "  • Find 'SynapseFlow AI' in your application menu"
echo "  • Launch from Activities or Krunner"
echo "  • Use system tray integration"
echo "  • Right-click text files to send to SynapseFlow AI"
echo ""
echo "To start the application:"
echo "  1. Search for 'SynapseFlow AI' in the application launcher"
echo "  2. Or run: $PROJECT_DIR/scripts/launch_kde.sh"
echo ""
echo "First run will prompt you to configure your .env file."