#!/usr/bin/env python3
"""
Test Runner Script
Runs comprehensive tests for SynapseFlow AI system.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_command(cmd, description="", check=True):
    """Run a command and handle output"""
    print(f"\n{'='*60}")
    print(f"🔄 {description or cmd}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr and result.returncode != 0:
            print(f"ERROR: {result.stderr}")

        print(f"✅ Command completed with return code: {result.returncode}")
        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def check_dependencies():
    """Check if all test dependencies are available"""
    print("📦 Checking test dependencies...")

    required_packages = [
        'pytest',
        'pytest-asyncio',
        'pytest-cov',
        'pytest-mock'
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False

    print("✅ All test dependencies available")
    return True


def run_unit_tests():
    """Run unit tests for individual components"""
    print("\n🧪 Running Unit Tests")

    test_files = [
        'tests/test_config_validator.py',
        'tests/test_health_checker.py',
        'tests/test_secure_config.py',
        'tests/test_webhook_manager.py'
    ]

    success_count = 0
    for test_file in test_files:
        if os.path.exists(test_file):
            success = run_command(
                f"python -m pytest {test_file} -v",
                f"Running {test_file}",
                check=False
            )
            if success:
                success_count += 1
        else:
            print(f"⚠️  Test file not found: {test_file}")

    print(f"\n📊 Unit Tests Summary: {success_count}/{len(test_files)} passed")
    return success_count == len(test_files)


def run_integration_tests():
    """Run integration tests"""
    print("\n🔗 Running Integration Tests")

    # Set test environment variables
    test_env = os.environ.copy()
    test_env.update({
        'ENVIRONMENT': 'development',
        'DEBUG': '1',
        'USE_OPENAI': '0',  # Disable for testing
        'OLLAMA_DISABLE': '1',  # Disable for testing
        'CONFIG_VALIDATION_STRICT': '0',  # Lenient for testing
    })

    success = run_command(
        "python -m pytest tests/test_integration.py -v -k 'TestNewFeaturesIntegration or TestProductionReadinessIntegration'",
        "Running New Features Integration Tests",
        check=False
    )

    return success


def run_coverage_tests():
    """Run tests with coverage reporting"""
    print("\n📊 Running Coverage Tests")

    success = run_command(
        "python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing",
        "Running Coverage Analysis",
        check=False
    )

    if success and os.path.exists('htmlcov/index.html'):
        print("📊 Coverage report generated: htmlcov/index.html")

    return success


def run_linting():
    """Run code linting"""
    print("\n🧹 Running Code Linting")

    # Check if flake8 is available
    try:
        import flake8
        success = run_command(
            "python -m flake8 utils/ security/ integrations/ ai/ --max-line-length=100 --ignore=E203,W503",
            "Running flake8 linting",
            check=False
        )
        return success
    except ImportError:
        print("⚠️  flake8 not available, skipping linting")
        return True


def run_type_checking():
    """Run type checking with mypy"""
    print("\n🔍 Running Type Checking")

    try:
        import mypy
        success = run_command(
            "python -m mypy utils/ security/ integrations/ ai/ --ignore-missing-imports",
            "Running mypy type checking",
            check=False
        )
        return success
    except ImportError:
        print("⚠️  mypy not available, skipping type checking")
        return True


def run_security_scan():
    """Run security scanning"""
    print("\n🔒 Running Security Scan")

    try:
        import bandit
        success = run_command(
            "python -m bandit -r . -f json -o security_scan.json -x tests/,venv/,.venv/",
            "Running bandit security scan",
            check=False
        )

        if os.path.exists('security_scan.json'):
            print("🔒 Security scan results saved to security_scan.json")

        return success
    except ImportError:
        print("⚠️  bandit not available, skipping security scan")
        return True


def validate_system_config():
    """Validate system configuration"""
    print("\n⚙️  Validating System Configuration")

    success = run_command(
        "python -c 'from utils.config_validator import validate_environment; print(\"Config validation:\", validate_environment())'",
        "Validating configuration",
        check=False
    )

    return success


def test_database_initialization():
    """Test database initialization"""
    print("\n💾 Testing Database Initialization")

    import tempfile
    temp_dir = tempfile.mkdtemp()

    success = run_command(
        f"python scripts/init_database.py {temp_dir}",
        f"Testing database initialization in {temp_dir}",
        check=False
    )

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    return success


def main():
    """Main test runner"""
    print("🚀 SynapseFlow AI Test Suite")
    print("=" * 60)

    # Change to project directory
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)

    # Track results
    results = {}

    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Missing dependencies. Please install required packages.")
        sys.exit(1)

    # Run test categories
    test_categories = [
        ("Validate System Config", validate_system_config),
        ("Database Initialization", test_database_initialization),
        ("Unit Tests", run_unit_tests),
        ("Integration Tests", run_integration_tests),
        ("Code Linting", run_linting),
        ("Type Checking", run_type_checking),
        ("Security Scan", run_security_scan),
        ("Coverage Tests", run_coverage_tests),
    ]

    for name, test_func in test_categories:
        results[name] = test_func()

    # Final summary
    print("\n" + "=" * 60)
    print("📋 FINAL TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for success in results.values() if success)
    total = len(results)

    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")

    print(f"\n📊 Overall: {passed}/{total} test categories passed")

    if passed == total:
        print("\n🎉 All tests passed! System is ready for deployment.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test categories failed. Please review and fix issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()