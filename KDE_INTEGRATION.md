# 🐧 KDE Plasma Integration Guide

This guide shows you how to integrate SynapseFlow AI natively with KDE Plasma desktop environment.

## 🚀 Quick KDE Installation

Run the automated installer:

```bash
./scripts/install_kde_integration.sh
```

This will:
- Install system tray integration
- Add SynapseFlow AI to your application menu
- Create desktop shortcuts and actions
- Set up right-click context menus for text files
- Install native KDE notifications

## 📋 Manual Installation Steps

If you prefer manual installation:

### 1. Install Dependencies

#### PyQt5 (for system tray):
```bash
# Ubuntu/Debian
sudo apt install python3-pyqt5

# Arch Linux
sudo pacman -S python-pyqt5

# Fedora
sudo dnf install python3-qt5

# openSUSE
sudo zypper install python3-qt5
```

### 2. Install Desktop Integration

```bash
# Copy desktop file
mkdir -p ~/.local/share/applications
cp desktop/synapseflow-ai.desktop ~/.local/share/applications/

# Copy icon
mkdir -p ~/.local/share/icons/hicolor/48x48/apps
cp desktop/synapseflow-ai.png ~/.local/share/icons/hicolor/48x48/apps/

# Update desktop database
update-desktop-database ~/.local/share/applications
gtk-update-icon-cache ~/.local/share/icons/hicolor
```

### 3. Make Scripts Executable

```bash
chmod +x scripts/launch_kde.sh
chmod +x scripts/send_to_synapseflow.sh
```

## 🎯 KDE Features

### Application Launcher
- Search for "SynapseFlow AI" in KRunner (Alt+Space)
- Find it in Application Menu → Internet or Office
- Pin to taskbar or desktop

### System Tray Integration
- Persistent system tray icon
- Context menu with quick actions:
  - Open Dashboard
  - Admin Interface
  - Check Status
  - Quit Application
- Real-time health monitoring
- Native KDE notifications

### Desktop Actions
Right-click on the application icon for:
- **Open Dashboard** - Monitoring interface
- **Admin Interface** - Administrative controls
- **View Logs** - Real-time log viewing in Konsole

### File Integration
- Right-click any text file → "Send to SynapseFlow AI"
- Automatically processes file content through AI
- Shows response in native KDE dialog

## 🖥️ Using the KDE Interface

### First Launch
1. Launch "SynapseFlow AI" from application menu
2. System will prompt to configure `.env` file
3. Kate/KWrite will open for configuration
4. Save and close to continue startup

### System Tray Operations
- **Left Click**: Show/hide main dashboard
- **Right Click**: Context menu with actions
- **Middle Click**: Quick status check

### Notifications
The system shows KDE notifications for:
- Application startup/shutdown
- Health status changes
- Error conditions
- Configuration updates

## ⚙️ Configuration

### KDE-Specific Settings

The launcher script supports KDE-specific environment variables:

```bash
# In your ~/.bashrc or ~/.profile
export SYNAPSEFLOW_KDE_NOTIFICATIONS=1  # Enable KDE notifications
export SYNAPSEFLOW_KDE_SYSTRAY=1        # Enable system tray
export SYNAPSEFLOW_KDE_AUTOSTART=1      # Start with KDE session
```

### Autostart Setup

To start SynapseFlow AI automatically with KDE:

```bash
# Create autostart entry
mkdir -p ~/.config/autostart
cp desktop/synapseflow-ai.desktop ~/.config/autostart/
```

### Custom Icon

Replace the default icon:

```bash
# Use your own icon
cp /path/to/your/icon.png desktop/synapseflow-ai.png

# Update installations
./scripts/install_kde_integration.sh
```

## 🔧 Troubleshooting

### System Tray Not Appearing
```bash
# Check if PyQt5 is installed
python3 -c "import PyQt5; print('PyQt5 OK')"

# Enable system tray in KDE
systemsettings5  # → Appearance → Application Style → Widget Style → Configure → Show icons in system tray
```

### Application Not in Menu
```bash
# Refresh application database
update-desktop-database ~/.local/share/applications
kbuildsycoca5 --noincremental
```

### Notifications Not Working
```bash
# Test KDE notifications
kdialog --passivepopup "Test notification" 3

# Check notification settings
systemsettings5  # → Notifications
```

### File Context Menu Missing
```bash
# Refresh KDE service menus
kbuildsycoca5 --noincremental

# Check service menu location
ls ~/.local/share/kservices5/ServiceMenus/
```

## 🎨 Customization

### Change Application Icon
1. Create/download a 48x48 PNG icon
2. Save as `desktop/synapseflow-ai.png`
3. Run `./scripts/install_kde_integration.sh` to update

### Modify Desktop Actions
Edit `desktop/synapseflow-ai.desktop`:

```ini
[Desktop Action custom]
Name=Custom Action
Icon=custom-icon
Exec=/path/to/custom/script.sh
```

### Custom System Tray Menu
Modify the PyQt5 section in `scripts/launch_kde.sh` to add custom menu items.

## 🚀 Advanced Integration

### KDE Plasma Widgets
Create a Plasma widget for quick access:

```bash
# Install Plasma development tools
sudo apt install plasma-framework-dev  # Ubuntu/Debian
sudo pacman -S plasma-framework        # Arch Linux

# Create widget directory
mkdir -p ~/.local/share/plasma/plasmoids/org.synapseflow.widget
```

### KWin Window Rules
Set up window management rules:

```bash
# System Settings → Window Management → Window Rules
# Create rule for "SynapseFlow AI" windows
```

### Global Shortcuts
Set up keyboard shortcuts:

```bash
# System Settings → Shortcuts → Custom Shortcuts
# Add shortcut to launch SynapseFlow AI
```

## 📱 Mobile Integration

For KDE Connect integration:

```bash
# Enable KDE Connect plugin development
mkdir -p ~/.local/share/kdeconnect/plugins/synapseflow

# Create plugin for mobile SMS integration
# (Advanced - requires KDE Connect plugin development)
```

## 🔄 Updates and Maintenance

### Updating Integration
```bash
# Pull latest changes
git pull origin main

# Reinstall KDE integration
./scripts/install_kde_integration.sh
```

### Cleaning Up
```bash
# Remove desktop integration
rm ~/.local/share/applications/synapseflow-ai.desktop
rm ~/.local/share/icons/hicolor/48x48/apps/synapseflow-ai.png
rm -rf ~/.local/share/kservices5/ServiceMenus/synapseflow-ai.desktop
rm ~/.config/autostart/synapseflow-ai.desktop

# Refresh databases
update-desktop-database ~/.local/share/applications
gtk-update-icon-cache ~/.local/share/icons/hicolor
kbuildsycoca5 --noincremental
```

## 🛡️ Security Considerations

### File Permissions
- Desktop files are installed in user directory (`~/.local/`)
- No system-wide modifications required
- Scripts run with user permissions only

### Network Security
- Application runs on localhost only by default
- Configure firewall rules if external access needed
- Use HTTPS in production deployments

## 📚 Additional Resources

- **KDE Development**: https://develop.kde.org/
- **PyQt5 Documentation**: https://doc.qt.io/qtforpython/
- **Desktop Entry Specification**: https://specifications.freedesktop.org/desktop-entry-spec/
- **KDE System Tray**: https://userbase.kde.org/System_Tray

## 🆘 Getting Help

If you encounter issues:

1. Check the application logs: `tail -f synapseflow_data/logs/app/app.log`
2. Test basic functionality: `curl http://localhost:8081/health`
3. Verify KDE environment: `echo $XDG_CURRENT_DESKTOP`
4. Check PyQt5 installation: `python3 -c "import PyQt5"`

For KDE-specific issues, consult the KDE community forums or documentation.

---

**🎉 Enjoy your native KDE Plasma integration with SynapseFlow AI!**