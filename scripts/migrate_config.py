#!/usr/bin/env python3
"""
Configuration Migration Script
Migrates existing .env configuration to secure encrypted storage.
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.secure_config import get_config_manager
from utils.config_validator import validate_environment


def backup_existing_env():
    """Backup existing .env file"""
    env_file = Path('.env')
    if env_file.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = Path(f'.env.backup_{timestamp}')
        shutil.copy2(env_file, backup_file)
        print(f"✅ Backed up existing .env to {backup_file}")
        return backup_file
    return None


def generate_secure_secrets():
    """Generate secure random secrets for production"""
    import secrets
    import string

    def generate_secret(length=32):
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    return {
        'ADMIN_SECRET': generate_secret(48),
        'LICENSE_ISSUER_SECRET': generate_secret(48),
    }


def migrate_configuration():
    """Main migration function"""
    print("🔄 Starting configuration migration to secure storage...")

    # Step 1: Backup existing configuration
    backup_file = backup_existing_env()

    # Step 2: Validate current environment
    print("\n📋 Validating current configuration...")
    try:
        is_valid = validate_environment()
        if not is_valid:
            print("⚠️  Configuration validation found issues. Migration will continue but please review.")
    except Exception as e:
        print(f"⚠️  Configuration validation failed: {e}")

    # Step 3: Initialize secure config manager
    print("\n🔐 Initializing secure configuration manager...")
    config_manager = get_config_manager()

    # Step 4: Import current environment variables
    print("📥 Importing environment variables to secure storage...")
    imported_count = config_manager.import_from_env()
    print(f"✅ Imported {imported_count} configuration values")

    # Step 5: Generate secure secrets for production
    print("\n🔑 Generating secure secrets...")
    secure_secrets = generate_secure_secrets()

    for key, value in secure_secrets.items():
        if not os.getenv(key) or os.getenv(key) in ['change-me', 'please-change-this', 'generate-secure-random-string']:
            config_manager.set_config(key, value, save_immediately=False)
            print(f"✅ Generated secure {key}")

    # Step 6: Save all configurations
    print("\n💾 Saving secure configuration...")
    config_manager._save_config_file(config_manager._config_cache)

    # Step 7: Validate migrated configuration
    print("\n🔍 Validating migrated configuration...")
    validation_result = config_manager.validate_config()

    if validation_result['valid']:
        print("✅ Configuration validation passed!")
    else:
        print("⚠️  Configuration validation issues found:")
        for error in validation_result['missing_required']:
            print(f"  - Missing: {error['key']} ({error['description']})")

    # Step 8: Create new .env file with non-sensitive values
    print("\n📝 Creating new .env file with non-sensitive values...")
    config_manager.export_to_env_file('.env.new', include_secrets=False)

    print("\n🎉 Migration completed successfully!")
    print("\n📋 Next steps:")
    print("1. Review .env.new and rename it to .env if satisfied")
    print("2. Update your deployment scripts to use the secure configuration")
    print("3. Test the application with the new configuration")
    print("4. Remove .env.backup_* files after confirming everything works")

    if backup_file:
        print(f"5. Your original configuration is backed up at {backup_file}")


def create_development_env():
    """Create a development environment file"""
    print("\n🛠️  Creating development environment...")

    config_manager = get_config_manager()

    # Set development-specific configurations
    dev_config = {
        'ENVIRONMENT': 'development',
        'DEBUG': '1',
        'ADMIN_DEBUG': '1',
        'LOG_FORMAT': 'text',
        'CONFIG_VALIDATION_STRICT': '0',
        'LICENSE_ENFORCE': '0',
        'ENABLE_METRICS': '1',
    }

    for key, value in dev_config.items():
        config_manager.set_config(key, value, save_immediately=False)

    config_manager.export_to_env_file('.env.development', include_secrets=False)
    print("✅ Created .env.development for development environment")


def create_production_env():
    """Create a production environment template"""
    print("\n🚀 Creating production environment template...")

    config_manager = get_config_manager()

    # Set production-specific configurations
    prod_config = {
        'ENVIRONMENT': 'production',
        'DEBUG': '0',
        'ADMIN_DEBUG': '0',
        'LOG_FORMAT': 'json',
        'CONFIG_VALIDATION_STRICT': '1',
        'LICENSE_ENFORCE': '1',
        'ENABLE_METRICS': '1',
    }

    for key, value in prod_config.items():
        config_manager.set_config(key, value, save_immediately=False)

    config_manager.export_to_env_file('.env.production.template', include_secrets=False)
    print("✅ Created .env.production.template for production deployment")
    print("⚠️  Remember to configure actual API keys and secrets for production!")


def main():
    """Main entry point"""
    print("🔧 SynapseFlow AI Configuration Migration Tool")
    print("=" * 50)

    if len(sys.argv) < 2:
        print("Usage: python migrate_config.py <command>")
        print("\nCommands:")
        print("  migrate     - Migrate current configuration to secure storage")
        print("  dev-env     - Create development environment")
        print("  prod-env    - Create production environment template")
        print("  validate    - Validate current configuration")
        return

    command = sys.argv[1].lower()

    try:
        if command == 'migrate':
            migrate_configuration()
        elif command == 'dev-env':
            create_development_env()
        elif command == 'prod-env':
            create_production_env()
        elif command == 'validate':
            print("🔍 Validating configuration...")
            is_valid = validate_environment()
            if is_valid:
                print("✅ Configuration is valid!")
            else:
                print("❌ Configuration validation failed!")
                sys.exit(1)
        else:
            print(f"❌ Unknown command: {command}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()