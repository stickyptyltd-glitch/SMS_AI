#!/bin/bash
"""
KDE Launch Script for SynapseFlow AI
Provides native KDE integration with system tray and notifications
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# KDE integration functions
show_kde_notification() {
    local title="$1"
    local message="$2"
    local icon="${3:-dialog-information}"

    if command -v kdialog &> /dev/null; then
        kdialog --title "$title" --passivepopup "$message" 5
    elif command -v notify-send &> /dev/null; then
        notify-send -i "$icon" "$title" "$message"
    fi
}

# Check if already running
if pgrep -f "python.*server.py" > /dev/null; then
    show_kde_notification "SynapseFlow AI" "Application is already running!"

    # Open dashboard in browser
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:8081/monitoring/dashboard"
    fi
    exit 0
fi

cd "$PROJECT_DIR"

# Check virtual environment
if [ ! -d ".venv" ]; then
    show_kde_notification "SynapseFlow AI" "Setting up virtual environment..." "dialog-information"

    if ! python3 -m venv .venv; then
        show_kde_notification "SynapseFlow AI" "Failed to create virtual environment!" "dialog-error"
        exit 1
    fi

    source .venv/bin/activate
    pip install -r requirements-server.txt
else
    source .venv/bin/activate
fi

# Check configuration
if [ ! -f ".env" ]; then
    show_kde_notification "SynapseFlow AI" "First run - opening configuration..." "dialog-information"

    # Copy example config
    cp .env.example .env

    # Open config file in KDE text editor
    if command -v kate &> /dev/null; then
        kate .env &
    elif command -v kwrite &> /dev/null; then
        kwrite .env &
    else
        xdg-open .env &
    fi

    kdialog --msgbox "Please configure your .env file with your API keys and settings, then restart SynapseFlow AI."
    exit 0
fi

# Initialize database if needed
if [ ! -d "synapseflow_data" ]; then
    show_kde_notification "SynapseFlow AI" "Initializing database..." "dialog-information"
    python scripts/init_database.py
fi

# Start the application
show_kde_notification "SynapseFlow AI" "Starting SynapseFlow AI..." "dialog-information"

# Start main server in background
python server.py &
SERVER_PID=$!

# Wait a moment for server to start
sleep 3

# Check if server started successfully
if ! kill -0 $SERVER_PID 2>/dev/null; then
    show_kde_notification "SynapseFlow AI" "Failed to start main server!" "dialog-error"
    exit 1
fi

# Start admin server if enabled
if grep -q "ADMIN_PORT=" .env && ! grep -q "ADMIN_PORT=$" .env; then
    python admin_server.py &
    ADMIN_PID=$!
fi

show_kde_notification "SynapseFlow AI" "Application started successfully!\nDashboard: http://localhost:8081/monitoring/dashboard" "dialog-information"

# Create system tray integration using Python/Qt if available
python3 << 'EOF'
import sys
import os
import subprocess
import signal
from pathlib import Path

try:
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
    from PyQt5.QtGui import QIcon
    from PyQt5.QtCore import QTimer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

if PYQT_AVAILABLE:
    class SynapseFlowTray:
        def __init__(self):
            self.app = QApplication([])
            self.app.setQuitOnLastWindowClosed(False)

            # Create system tray icon
            self.tray = QSystemTrayIcon()

            # Try to load icon
            icon_path = Path(__file__).parent.parent / "desktop" / "synapseflow-ai.png"
            if icon_path.exists():
                self.tray.setIcon(QIcon(str(icon_path)))
            else:
                self.tray.setIcon(self.app.style().standardIcon(self.app.style().SP_ComputerIcon))

            self.tray.setToolTip("SynapseFlow AI - AI-Powered SMS Assistant")

            # Create context menu
            menu = QMenu()

            dashboard_action = QAction("Open Dashboard", menu)
            dashboard_action.triggered.connect(self.open_dashboard)
            menu.addAction(dashboard_action)

            admin_action = QAction("Admin Interface", menu)
            admin_action.triggered.connect(self.open_admin)
            menu.addAction(admin_action)

            menu.addSeparator()

            status_action = QAction("Check Status", menu)
            status_action.triggered.connect(self.check_status)
            menu.addAction(status_action)

            menu.addSeparator()

            quit_action = QAction("Quit", menu)
            quit_action.triggered.connect(self.quit_application)
            menu.addAction(quit_action)

            self.tray.setContextMenu(menu)
            self.tray.show()

            # Setup status checker
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self.check_server_status)
            self.status_timer.start(30000)  # Check every 30 seconds

            self.tray.showMessage(
                "SynapseFlow AI",
                "Application is running in system tray",
                QSystemTrayIcon.Information,
                3000
            )

        def open_dashboard(self):
            subprocess.Popen(['xdg-open', 'http://localhost:8081/monitoring/dashboard'])

        def open_admin(self):
            subprocess.Popen(['xdg-open', 'http://localhost:5050'])

        def check_status(self):
            try:
                import requests
                response = requests.get('http://localhost:8081/health', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.tray.showMessage(
                        "System Status",
                        f"Status: {data.get('status', 'Unknown')}\nServices: {len(data.get('services', {}))} active",
                        QSystemTrayIcon.Information,
                        5000
                    )
                else:
                    self.tray.showMessage(
                        "System Status",
                        "Server is running but health check failed",
                        QSystemTrayIcon.Warning,
                        5000
                    )
            except Exception as e:
                self.tray.showMessage(
                    "System Status",
                    f"Unable to connect to server: {str(e)}",
                    QSystemTrayIcon.Critical,
                    5000
                )

        def check_server_status(self):
            # Silently check if server is still running
            try:
                import requests
                requests.get('http://localhost:8081/health', timeout=2)
            except:
                self.tray.showMessage(
                    "SynapseFlow AI",
                    "Server appears to be down!",
                    QSystemTrayIcon.Critical,
                    10000
                )

        def quit_application(self):
            # Kill server processes
            try:
                subprocess.run(['pkill', '-f', 'server.py'], check=False)
                subprocess.run(['pkill', '-f', 'admin_server.py'], check=False)
            except:
                pass

            self.tray.showMessage(
                "SynapseFlow AI",
                "Application shutting down...",
                QSystemTrayIcon.Information,
                2000
            )

            self.app.quit()

        def run(self):
            sys.exit(self.app.exec_())

    if __name__ == '__main__':
        tray_app = SynapseFlowTray()
        tray_app.run()

else:
    # Fallback: just wait for user input
    print("SynapseFlow AI is running...")
    print("Dashboard: http://localhost:8081/monitoring/dashboard")
    print("Admin: http://localhost:5050")
    print("Press Ctrl+C to stop")

    try:
        # Keep script alive
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        subprocess.run(['pkill', '-f', 'server.py'], check=False)
        subprocess.run(['pkill', '-f', 'admin_server.py'], check=False)
        sys.exit(0)
EOF