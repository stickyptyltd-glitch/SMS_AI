#!/usr/bin/env python3
"""
Comprehensive System Health Check
Validates all components, dependencies, and configurations.
"""

import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple, Any
import importlib.util

class HealthChecker:
    """Comprehensive system health checker"""
    
    def __init__(self):
        self.results = []
        self.errors = []
        self.warnings = []
        self.server_url = "http://127.0.0.1:8081"
    
    def log_result(self, component: str, status: str, message: str, details: Any = None):
        """Log a health check result"""
        result = {
            "component": component,
            "status": status,  # "pass", "fail", "warning"
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }
        self.results.append(result)
        
        if status == "fail":
            self.errors.append(f"{component}: {message}")
        elif status == "warning":
            self.warnings.append(f"{component}: {message}")
    
    def check_python_version(self):
        """Check Python version compatibility"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            self.log_result("Python Version", "pass", f"Python {version.major}.{version.minor}.{version.micro}")
        elif version.major == 3 and version.minor >= 6:
            self.log_result("Python Version", "warning", f"Python {version.major}.{version.minor}.{version.micro} - Consider upgrading to 3.8+")
        else:
            self.log_result("Python Version", "fail", f"Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.6+")
    
    def check_dependencies(self):
        """Check required dependencies"""
        required_packages = [
            ("flask", "Flask web framework"),
            ("requests", "HTTP library"),
            ("psutil", "System monitoring"),
            ("python-dotenv", "Environment variables")
        ]
        
        optional_packages = [
            ("pytest", "Testing framework"),
            ("openai", "OpenAI API client")
        ]
        
        for package, description in required_packages:
            try:
                importlib.import_module(package.replace("-", "_"))
                self.log_result(f"Dependency: {package}", "pass", f"{description} - Available")
            except ImportError:
                self.log_result(f"Dependency: {package}", "fail", f"{description} - Missing (pip install {package})")
        
        for package, description in optional_packages:
            try:
                importlib.import_module(package.replace("-", "_"))
                self.log_result(f"Optional: {package}", "pass", f"{description} - Available")
            except ImportError:
                self.log_result(f"Optional: {package}", "warning", f"{description} - Missing (pip install {package})")
    
    def check_file_structure(self):
        """Check required files and directories"""
        required_files = [
            "server.py",
            "user_management.py",
            "ai/analysis.py",
            "ai/generator.py",
            "ai/conversation_context.py",
            "analytics/system_monitor.py",
            "utils/error_handling.py",
            "security/advanced_security.py"
        ]
        
        required_dirs = [
            "ai/",
            "analytics/",
            "utils/",
            "security/",
            "tests/"
        ]
        
        for file_path in required_files:
            if os.path.exists(file_path):
                self.log_result(f"File: {file_path}", "pass", "File exists")
            else:
                self.log_result(f"File: {file_path}", "fail", "File missing")
        
        for dir_path in required_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                self.log_result(f"Directory: {dir_path}", "pass", "Directory exists")
            else:
                self.log_result(f"Directory: {dir_path}", "fail", "Directory missing")
    
    def check_configuration(self):
        """Check configuration files and environment variables"""
        # Check .env file
        if os.path.exists(".env"):
            self.log_result("Configuration: .env", "pass", ".env file exists")
            
            # Check for required environment variables
            with open(".env", "r") as f:
                env_content = f.read()
                
            required_vars = ["OPENAI_API_KEY", "USE_OPENAI", "ADMIN_TOKEN"]
            for var in required_vars:
                if var in env_content:
                    self.log_result(f"Config: {var}", "pass", f"{var} configured")
                else:
                    self.log_result(f"Config: {var}", "warning", f"{var} not configured")
        else:
            self.log_result("Configuration: .env", "warning", ".env file missing - copy from .env.example")
        
        # Check .env.example
        if os.path.exists(".env.example"):
            self.log_result("Configuration: .env.example", "pass", "Example configuration exists")
        else:
            self.log_result("Configuration: .env.example", "warning", "Example configuration missing")
    
    def check_data_directories(self):
        """Check data directories and permissions"""
        data_dirs = [
            "dayle_data/",
            "dayle_data/users/",
            "dayle_data/conversations/",
            "dayle_data/analytics/",
            "dayle_data/security/"
        ]
        
        for dir_path in data_dirs:
            if os.path.exists(dir_path):
                if os.access(dir_path, os.R_OK | os.W_OK):
                    self.log_result(f"Data Dir: {dir_path}", "pass", "Directory accessible")
                else:
                    self.log_result(f"Data Dir: {dir_path}", "fail", "Directory not writable")
            else:
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    self.log_result(f"Data Dir: {dir_path}", "pass", "Directory created")
                except Exception as e:
                    self.log_result(f"Data Dir: {dir_path}", "fail", f"Cannot create directory: {e}")
    
    def check_server_startup(self):
        """Check if server can start up"""
        try:
            # Try to import server module
            import server
            self.log_result("Server Import", "pass", "Server module imports successfully")
            
            # Check if Flask app is created
            if hasattr(server, 'app'):
                self.log_result("Flask App", "pass", "Flask application created")
            else:
                self.log_result("Flask App", "fail", "Flask application not found")
                
        except Exception as e:
            self.log_result("Server Import", "fail", f"Server import failed: {e}")
    
    def check_server_endpoints(self):
        """Check if server is running and endpoints are accessible"""
        try:
            # Check health endpoint
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_result("Server Health", "pass", "Server is running and healthy")
                
                # Check other key endpoints
                endpoints_to_check = [
                    ("/", "Landing page"),
                    ("/config", "Configuration endpoint"),
                    ("/profile", "Profile endpoint"),
                    ("/users/roles", "User roles endpoint")
                ]
                
                for endpoint, description in endpoints_to_check:
                    try:
                        resp = requests.get(f"{self.server_url}{endpoint}", timeout=3)
                        if resp.status_code in [200, 401, 403]:  # 401/403 are ok for protected endpoints
                            self.log_result(f"Endpoint: {endpoint}", "pass", f"{description} accessible")
                        else:
                            self.log_result(f"Endpoint: {endpoint}", "warning", f"{description} returned {resp.status_code}")
                    except Exception as e:
                        self.log_result(f"Endpoint: {endpoint}", "warning", f"{description} check failed: {e}")
                        
            else:
                self.log_result("Server Health", "fail", f"Server returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.log_result("Server Health", "warning", "Server not running - start with 'python server.py'")
        except Exception as e:
            self.log_result("Server Health", "fail", f"Server health check failed: {e}")
    
    def check_ai_components(self):
        """Check AI components and functionality"""
        try:
            from ai.analysis import analyze
            from ai.generator import build_reply_prompt
            from ai.conversation_context import ConversationContextManager
            
            self.log_result("AI Components", "pass", "AI modules import successfully")
            
            # Test basic analysis
            try:
                # Mock the required parameters
                mock_profile = {"style_rules": [], "preferred_phrases": [], "banned_words": []}
                mock_ollama_fn = lambda x: {"sentiment": "positive", "intent": "greeting"}

                analysis = analyze("Hello, how are you?", "TestContact", mock_profile, mock_ollama_fn)
                if isinstance(analysis, dict) and "sentiment" in analysis:
                    self.log_result("AI Analysis", "pass", "Message analysis working")
                else:
                    self.log_result("AI Analysis", "warning", "Analysis returned unexpected format")
            except Exception as e:
                self.log_result("AI Analysis", "fail", f"Analysis failed: {e}")
            
            # Test conversation context
            try:
                context_manager = ConversationContextManager()
                personality = context_manager.load_personality("default")
                if personality:
                    self.log_result("Conversation Context", "pass", "Context management working")
                else:
                    self.log_result("Conversation Context", "warning", "Default personality not found")
            except Exception as e:
                self.log_result("Conversation Context", "fail", f"Context management failed: {e}")
                
        except Exception as e:
            self.log_result("AI Components", "fail", f"AI components import failed: {e}")
    
    def check_security_components(self):
        """Check security components"""
        try:
            from security.advanced_security import SecurityMonitor, RateLimiter
            from utils.error_handling import InputValidator
            
            self.log_result("Security Components", "pass", "Security modules import successfully")
            
            # Test input validation
            try:
                is_valid = InputValidator.validate_email("test@example.com")
                if is_valid:
                    self.log_result("Input Validation", "pass", "Input validation working")
                else:
                    self.log_result("Input Validation", "fail", "Input validation not working correctly")
            except Exception as e:
                self.log_result("Input Validation", "fail", f"Input validation failed: {e}")
            
            # Test rate limiting
            try:
                rate_limiter = RateLimiter()
                limited, reset_time = rate_limiter.is_rate_limited("test_ip", "default")
                self.log_result("Rate Limiting", "pass", "Rate limiting working")
            except Exception as e:
                self.log_result("Rate Limiting", "fail", f"Rate limiting failed: {e}")
                
        except Exception as e:
            self.log_result("Security Components", "fail", f"Security components import failed: {e}")
    
    def check_user_management(self):
        """Check user management system"""
        try:
            from user_management import UserManager
            
            user_manager = UserManager()
            self.log_result("User Management", "pass", "User management system working")
            
            # Check if we can load users
            try:
                users = user_manager.users
                self.log_result("User Storage", "pass", f"User storage accessible ({len(users)} users)")
            except Exception as e:
                self.log_result("User Storage", "warning", f"User storage issue: {e}")
                
        except Exception as e:
            self.log_result("User Management", "fail", f"User management failed: {e}")
    
    def check_analytics(self):
        """Check analytics and monitoring"""
        try:
            from analytics.system_monitor import SystemMonitor
            
            system_monitor = SystemMonitor()
            health = system_monitor.get_system_health()
            
            if "health_score" in health:
                score = health["health_score"]
                if score >= 80:
                    self.log_result("System Analytics", "pass", f"System health score: {score}")
                elif score >= 60:
                    self.log_result("System Analytics", "warning", f"System health score: {score}")
                else:
                    self.log_result("System Analytics", "fail", f"Low system health score: {score}")
            else:
                self.log_result("System Analytics", "warning", "Could not get system health score")
                
        except Exception as e:
            self.log_result("System Analytics", "fail", f"Analytics check failed: {e}")
    
    def run_all_checks(self):
        """Run all health checks"""
        print("🔍 Starting comprehensive system health check...")
        print("=" * 60)
        
        checks = [
            ("Python Version", self.check_python_version),
            ("Dependencies", self.check_dependencies),
            ("File Structure", self.check_file_structure),
            ("Configuration", self.check_configuration),
            ("Data Directories", self.check_data_directories),
            ("Server Startup", self.check_server_startup),
            ("Server Endpoints", self.check_server_endpoints),
            ("AI Components", self.check_ai_components),
            ("Security Components", self.check_security_components),
            ("User Management", self.check_user_management),
            ("Analytics", self.check_analytics)
        ]
        
        for check_name, check_func in checks:
            print(f"\n🔧 Checking {check_name}...")
            try:
                check_func()
            except Exception as e:
                self.log_result(check_name, "fail", f"Check failed with exception: {e}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print health check summary"""
        print("\n" + "=" * 60)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 60)
        
        # Count results
        passed = sum(1 for r in self.results if r["status"] == "pass")
        failed = sum(1 for r in self.results if r["status"] == "fail")
        warnings = sum(1 for r in self.results if r["status"] == "warning")
        total = len(self.results)
        
        print(f"✅ Passed: {passed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Total: {total}")
        
        # Overall health score
        health_score = (passed / total * 100) if total > 0 else 0
        print(f"\n🎯 Overall Health Score: {health_score:.1f}%")
        
        if health_score >= 90:
            print("🎉 System is in excellent health!")
        elif health_score >= 75:
            print("👍 System is in good health with minor issues.")
        elif health_score >= 50:
            print("⚠️  System has some issues that should be addressed.")
        else:
            print("🚨 System has critical issues that need immediate attention!")
        
        # Show errors and warnings
        if self.errors:
            print(f"\n❌ CRITICAL ISSUES ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if failed > 0:
            print("  • Fix critical issues before deploying to production")
        if warnings > 0:
            print("  • Address warnings to improve system reliability")
        if health_score < 90:
            print("  • Run health check regularly to monitor system status")
        
        print("\n📝 Detailed results saved to health_check_results.json")
        
        # Save detailed results
        with open("health_check_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "passed": passed,
                    "failed": failed,
                    "warnings": warnings,
                    "total": total,
                    "health_score": health_score
                },
                "results": self.results
            }, f, indent=2)

def main():
    """Main health check function"""
    checker = HealthChecker()
    checker.run_all_checks()
    
    # Exit with appropriate code
    if checker.errors:
        sys.exit(1)  # Critical issues found
    elif checker.warnings:
        sys.exit(2)  # Warnings found
    else:
        sys.exit(0)  # All good

if __name__ == "__main__":
    main()
