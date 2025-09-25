#!/usr/bin/env python3
"""
Local Deployment Script
Automates local deployment setup for SynapseFlow AI system.
"""

import os
import sys
import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")


def print_step(step, description):
    """Print deployment step"""
    print(f"\n{step}. {description}")
    print("-" * 40)


def run_command(cmd, description="", check=True, capture_output=True):
    """Run a command with proper error handling"""
    print(f"  ▶️  {description or cmd}")

    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=check
            )

            if result.returncode == 0:
                print(f"  ✅ Success")
                if result.stdout.strip():
                    print(f"  📝 {result.stdout.strip()}")
            else:
                print(f"  ❌ Failed (exit code: {result.returncode})")
                if result.stderr.strip():
                    print(f"  🚨 {result.stderr.strip()}")

            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True, check=check)
            return result.returncode == 0, "", ""

    except subprocess.CalledProcessError as e:
        print(f"  ❌ Command failed: {e}")
        return False, "", str(e)


def check_prerequisites():
    """Check system prerequisites"""
    print_step("1", "Checking Prerequisites")

    prerequisites = [
        ("python3", "Python 3.8+ is required"),
        ("pip", "pip package manager is required"),
    ]

    missing = []
    for cmd, description in prerequisites:
        success, stdout, stderr = run_command(f"which {cmd}", f"Checking {cmd}")
        if not success:
            missing.append(description)
            print(f"  ❌ {description}")
        else:
            print(f"  ✅ {description}")

    if missing:
        print(f"\n❌ Missing prerequisites:")
        for item in missing:
            print(f"  - {item}")
        return False

    # Check Python version
    success, version_output, _ = run_command("python3 --version", "Checking Python version")
    if success:
        print(f"  ✅ {version_output.strip()}")

    return True


def setup_virtual_environment():
    """Setup Python virtual environment"""
    print_step("2", "Setting up Virtual Environment")

    venv_path = ".venv"

    if os.path.exists(venv_path):
        print(f"  ℹ️  Virtual environment already exists at {venv_path}")
        activate_cmd = f"source {venv_path}/bin/activate"
    else:
        success, _, _ = run_command(
            f"python3 -m venv {venv_path}",
            f"Creating virtual environment at {venv_path}"
        )
        if not success:
            return False, None

        activate_cmd = f"source {venv_path}/bin/activate"

    print(f"  ✅ Virtual environment ready")
    print(f"  📝 Activate with: {activate_cmd}")

    return True, venv_path


def install_dependencies(venv_path):
    """Install Python dependencies"""
    print_step("3", "Installing Dependencies")

    # Activate virtual environment and install
    pip_cmd = f"{venv_path}/bin/pip"

    # Upgrade pip first
    success, _, _ = run_command(
        f"{pip_cmd} install --upgrade pip",
        "Upgrading pip"
    )

    if not success:
        return False

    # Install production dependencies
    success, _, _ = run_command(
        f"{pip_cmd} install -r requirements-server.txt",
        "Installing production dependencies"
    )

    if not success:
        return False

    # Install development dependencies if file exists
    if os.path.exists("requirements-dev.txt"):
        success, _, _ = run_command(
            f"{pip_cmd} install -r requirements-dev.txt",
            "Installing development dependencies"
        )

    print(f"  ✅ Dependencies installed")
    return True


def setup_configuration():
    """Setup configuration files"""
    print_step("4", "Setting up Configuration")

    # Check if .env exists
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            print("  ✅ Created .env from .env.example")
            print("  ⚠️  Please review and update .env with your configuration")
        else:
            print("  ❌ No .env.example file found")
            return False
    else:
        print("  ℹ️  .env file already exists")

    # Validate configuration
    try:
        from utils.config_validator import validate_environment
        is_valid = validate_environment()
        if is_valid:
            print("  ✅ Configuration validation passed")
        else:
            print("  ⚠️  Configuration validation found issues (check logs)")
    except Exception as e:
        print(f"  ⚠️  Could not validate configuration: {e}")

    return True


def initialize_databases():
    """Initialize databases and data directories"""
    print_step("5", "Initializing Databases and Storage")

    # Check if data directory already exists
    data_dir = os.getenv("DATA_DIR", "synapseflow_data")

    if os.path.exists(data_dir):
        print(f"  ℹ️  Data directory already exists: {data_dir}")

        # Ask user if they want to reinitialize
        response = input(f"  ❓ Reinitialize data directory? This will backup existing data. (y/N): ").lower()
        if response in ['y', 'yes']:
            # Create backup
            backup_name = f"{data_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move(data_dir, backup_name)
            print(f"  📦 Existing data backed up to: {backup_name}")
        else:
            print("  ⏭️  Skipping database initialization")
            return True

    # Run database initialization
    success, stdout, stderr = run_command(
        f"python scripts/init_database.py {data_dir}",
        f"Initializing databases in {data_dir}",
        capture_output=True
    )

    if not success:
        print(f"  ❌ Database initialization failed")
        if stderr:
            print(f"  🚨 Error: {stderr}")
        return False

    print(f"  ✅ Databases initialized successfully")
    return True


def migrate_configuration():
    """Migrate configuration to secure storage"""
    print_step("6", "Setting up Secure Configuration")

    # Ask user if they want to migrate to secure storage
    response = input("  ❓ Migrate to encrypted configuration storage? (y/N): ").lower()

    if response not in ['y', 'yes']:
        print("  ⏭️  Skipping secure configuration migration")
        return True

    success, stdout, stderr = run_command(
        "python scripts/migrate_config.py migrate",
        "Migrating to secure configuration",
        capture_output=True
    )

    if success:
        print("  ✅ Configuration migrated to secure storage")
        print("  📝 Review .env.new and replace .env if satisfied")
    else:
        print("  ⚠️  Configuration migration encountered issues")
        if stderr:
            print(f"  🚨 {stderr}")

    return True


def run_tests():
    """Run system tests"""
    print_step("7", "Running System Tests")

    # Ask user if they want to run tests
    response = input("  ❓ Run comprehensive test suite? This may take several minutes. (y/N): ").lower()

    if response not in ['y', 'yes']:
        print("  ⏭️  Skipping test suite")
        return True

    success, stdout, stderr = run_command(
        "python scripts/run_tests.py",
        "Running comprehensive test suite",
        capture_output=False,
        check=False
    )

    if success:
        print("  ✅ All tests passed")
    else:
        print("  ⚠️  Some tests failed - system may still be functional")

    return True


def start_services():
    """Start application services"""
    print_step("8", "Starting Services")

    print("  📋 Available services:")
    print("    • Main Server: python server.py")
    print("    • Admin Interface: python admin_server.py")

    # Check if user wants to start services now
    response = input("  ❓ Start main server now? (y/N): ").lower()

    if response in ['y', 'yes']:
        print("  🚀 Starting main server...")
        print("  📝 Server will start in foreground. Press Ctrl+C to stop.")
        print("  📝 Open a new terminal to run admin server if needed.")

        # Start server without capturing output so user can see logs
        try:
            subprocess.run("python server.py", shell=True, check=False)
        except KeyboardInterrupt:
            print("\n  ⏹️  Server stopped by user")

    else:
        print("  📝 To start services later:")
        print("    • Main server: python server.py")
        print("    • Admin server: python admin_server.py")
        print("    • Health check: curl http://localhost:8081/health")

    return True


def print_deployment_summary():
    """Print deployment summary and next steps"""
    print_header("Deployment Complete!")

    print("🎉 SynapseFlow AI has been deployed locally!")
    print("\n📋 Next Steps:")

    steps = [
        "Review your .env configuration file",
        "Start the main server: python server.py",
        "Start the admin interface: python admin_server.py",
        "Test the API: curl http://localhost:8081/health",
        "Visit admin interface: http://localhost:5050 (if enabled)",
        "Check logs in synapseflow_data/logs/ directory",
        "Run tests anytime: python scripts/run_tests.py"
    ]

    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")

    print("\n🔧 Configuration:")
    data_dir = os.getenv("DATA_DIR", "synapseflow_data")
    print(f"  • Data Directory: {data_dir}")
    print(f"  • Server Port: {os.getenv('SERVER_PORT', '8081')}")
    print(f"  • Admin Port: {os.getenv('ADMIN_PORT', '5050')}")

    print("\n📚 Documentation:")
    print("  • Check README.md for detailed usage instructions")
    print("  • Review .env.example for all configuration options")
    print("  • See AGENTS.md for contributor guidelines")

    print("\n🆘 Troubleshooting:")
    print("  • Check logs in synapseflow_data/logs/")
    print("  • Validate config: python -m utils.config_validator")
    print("  • Run health checks: python scripts/run_tests.py")


def main():
    """Main deployment function"""
    print_header("SynapseFlow AI Local Deployment")

    print("This script will set up SynapseFlow AI for local development/testing.")
    print("The process includes:")
    print("  • Checking prerequisites")
    print("  • Setting up virtual environment")
    print("  • Installing dependencies")
    print("  • Configuring the application")
    print("  • Initializing databases")
    print("  • Running tests")
    print("  • Starting services")

    # Confirm with user
    response = input("\n❓ Continue with deployment? (y/N): ").lower()
    if response not in ['y', 'yes']:
        print("❌ Deployment cancelled by user")
        sys.exit(0)

    # Change to project directory
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)
    print(f"📁 Working directory: {project_dir}")

    # Deployment steps
    deployment_steps = [
        ("Prerequisites", check_prerequisites),
        ("Virtual Environment", setup_virtual_environment),
        ("Dependencies", lambda venv=None: install_dependencies(venv) if venv else (False, None)),
        ("Configuration", setup_configuration),
        ("Databases", initialize_databases),
        ("Secure Config", migrate_configuration),
        ("Tests", run_tests),
        ("Services", start_services),
    ]

    venv_path = None

    for step_name, step_func in deployment_steps:
        try:
            if step_name == "Virtual Environment":
                success, venv_path = step_func()
            elif step_name == "Dependencies":
                success = step_func(venv_path)
            else:
                success = step_func()

            if not success and step_name in ["Prerequisites", "Virtual Environment", "Dependencies"]:
                print(f"\n❌ Critical step '{step_name}' failed. Cannot continue.")
                sys.exit(1)
            elif not success:
                print(f"\n⚠️  Step '{step_name}' failed but deployment can continue.")

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Deployment interrupted during '{step_name}'")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Unexpected error during '{step_name}': {e}")
            if step_name in ["Prerequisites", "Virtual Environment", "Dependencies"]:
                sys.exit(1)

    # Print summary
    print_deployment_summary()

    print(f"\n✅ Deployment completed at {datetime.now()}")


if __name__ == "__main__":
    main()