#!/usr/bin/env python3
"""
Diagnostic tool for the medical transcription application
This script helps identify common issues with database, Redis, and module imports
"""
import os
import sys
import platform
import importlib
import traceback
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


def print_header(message):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {message}")
    print("=" * 60)


def check_python_environment():
    """Check the Python environment"""
    print_header("Python Environment")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Executable: {sys.executable}")
    print(f"Prefix: {sys.prefix}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Sys path: {sys.path}")


def check_environment_variables():
    """Check critical environment variables"""
    print_header("Environment Variables")

    critical_vars = [
        'FLASK_APP', 'FLASK_ENV', 'FLASK_DEBUG', 'PORT',
        'DATABASE_URL', 'REDIS_URL', 'SECRET_KEY',
        'OPENAI_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS'
    ]

    for var in critical_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if var in ['DATABASE_URL', 'REDIS_URL', 'SECRET_KEY', 'OPENAI_API_KEY']:
                if len(value) > 10:
                    masked_value = value[:5] + '...' + value[-5:]
                else:
                    masked_value = '[SET]'
                print(f"{var}: {masked_value}")
            else:
                print(f"{var}: {value}")
        else:
            print(f"{var}: [NOT SET]")


def check_required_modules():
    """Check for required Python modules"""
    print_header("Required Modules")

    required_modules = [
        # Core Flask modules
        'flask', 'sqlalchemy', 'flask_sqlalchemy',
        # Authentication and security
        'bcrypt', 'jwt', 'flask_limiter',
        # Database
        'pg8000', 'redis',
        # API functionality
        'SpeechRecognition', 'deep_translator',
        # Cloud services
        'openai', 'google.cloud.speech',
        # Utilities
        'cryptography', 'pydub'
    ]

    for module_name in required_modules:
        try:
            module = importlib.import_module(module_name)
            try:
                version = getattr(module, '__version__', '[Unknown version]')
                print(f"✅ {module_name}: {version}")
            except:
                print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: Not found - {str(e)}")
        except Exception as e:
            print(f"⚠️ {module_name}: Error importing - {str(e)}")


def check_database_connection():
    """Check database connection"""
    print_header("Database Connection")

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL environment variable not set")
        return

    # Print masked URL
    masked_url = db_url
    if '@' in db_url:
        parts = db_url.split('@')
        credentials = parts[0].split(':')
        if len(credentials) > 2:
            credentials[2] = '***'  # Mask password
        parts[0] = ':'.join(credentials)
        masked_url = '@'.join(parts)

    print(f"Using database URL: {masked_url}")

    try:
        # Try SQLAlchemy connection
        print("\nTrying SQLAlchemy connection...")
        from sqlalchemy import create_engine, text
        import ssl

        # Create engine with appropriate URL conversion and SSL settings
        if db_url.startswith('postgres://'):
            engine_url = db_url.replace('postgres://', 'postgresql+pg8000://')
        elif db_url.startswith('postgresql://'):
            engine_url = db_url.replace('postgresql://', 'postgresql+pg8000://')
        else:
            engine_url = db_url

        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        engine = create_engine(
            engine_url,
            connect_args={"ssl_context": ssl_context},
            echo=True
        )

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"✅ PostgreSQL Version: {version}")

            # Check for tables
            result = conn.execute(text("""
                SELECT tablename FROM pg_catalog.pg_tables
                WHERE schemaname='public';
            """))
            tables = [row[0] for row in result]

            if tables:
                print(f"✅ Found {len(tables)} tables: {', '.join(tables)}")

                # Check expected tables
                expected_tables = ['users', 'transcriptions', 'translations', 'audit_logs']
                missing_tables = [table for table in expected_tables if table not in tables]

                if missing_tables:
                    print(f"❌ Missing expected tables: {', '.join(missing_tables)}")
                else:
                    print(f"✅ All expected tables are present")
            else:
                print("⚠️ No tables found in the 'public' schema")

    except Exception as e:
        print(f"❌ SQLAlchemy connection error: {str(e)}")
        print(f"\nError details:")
        traceback.print_exc()

        # Try pg8000 directly as a fallback
        try:
            print("\nTrying direct pg8000 connection...")
            import pg8000
            import ssl
            import urllib.parse as urlparse

            # Parse DB URL
            parsed = urlparse.urlparse(db_url)
            dbname = parsed.path[1:]  # Remove leading '/'
            user = parsed.username
            password = parsed.password
            host = parsed.hostname
            port = parsed.port or 5432

            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Connect with pg8000
            conn = pg8000.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                database=dbname,
                ssl_context=ssl_context
            )

            print("✅ Direct pg8000 connection successful!")

            # Execute a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ PostgreSQL Version: {version}")

            # Close connection
            conn.close()

        except Exception as e2:
            print(f"❌ Direct pg8000 connection also failed: {str(e2)}")


def check_redis_connection():
    """Check Redis connection"""
    print_header("Redis Connection")

    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        print("❌ REDIS_URL environment variable not set")
        return

    # Print masked URL
    safe_url = redis_url
    if '@' in redis_url:
        parts = redis_url.split('@')
        safe_url = f"redis://*****@{parts[1]}" if len(parts) > 1 else redis_url

    print(f"Using Redis URL: {safe_url}")

    try:
        import redis

        # Create Redis client
        client = redis.from_url(
            url=redis_url,
            socket_timeout=5,  # 5 second timeout
            socket_connect_timeout=5,
            retry_on_timeout=True
        )

        # Test connection
        ping_result = client.ping()
        print(f"✅ Redis PING successful: {ping_result}")

        # Try basic operations
        test_key = "diagnostic_test_key"
        test_value = "test_" + os.urandom(4).hex()

        # Set value
        set_result = client.set(test_key, test_value)
        print(f"✅ Redis SET operation: {set_result}")

        # Get value
        get_result = client.get(test_key)
        if get_result == test_value.encode():
            print(f"✅ Redis GET operation successful")
        else:
            print(f"⚠️ Redis GET operation returned unexpected result: {get_result}")

        # Delete key
        del_result = client.delete(test_key)
        print(f"✅ Redis DELETE operation: {del_result}")

        # Get server info
        info = client.info()
        print(f"\nRedis Server Information:")
        print(f"Version: {info.get('redis_version')}")
        print(f"Uptime: {info.get('uptime_in_days')} days")
        print(f"Connected clients: {info.get('connected_clients')}")
        print(f"Used memory: {info.get('used_memory_human')}")

    except redis.ConnectionError as e:
        print(f"❌ Redis connection error: {str(e)}")
    except Exception as e:
        print(f"❌ Redis error: {str(e)}")
        print(f"\nError details:")
        traceback.print_exc()


def check_file_permissions():
    """Check file permissions for required directories"""
    print_header("File Permissions")

    directories_to_check = [
        'uploads',
        'tts_output',
        'logs',
        '/tmp',
        os.path.join(os.getcwd(), 'uploads'),
        os.path.join(os.getcwd(), 'tts_output'),
        os.path.join(os.getcwd(), 'logs')
    ]

    for directory in directories_to_check:
        if os.path.exists(directory):
            # Check if directory is writable
            try:
                test_file = os.path.join(directory, f"test_write_{os.urandom(4).hex()}")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                print(f"✅ {directory}: Exists and is writable")
            except Exception as e:
                print(f"❌ {directory}: Not writable - {str(e)}")
        else:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ {directory}: Created successfully")
            except Exception as e:
                print(f"❌ {directory}: Could not create - {str(e)}")


def main():
    """Run all diagnostic checks"""
    print("🔍 Running diagnostic checks for Medical Transcription Application")

    check_python_environment()
    check_environment_variables()
    check_required_modules()
    check_database_connection()
    check_redis_connection()
    check_file_permissions()

    print("\n✅ Diagnostic checks completed!")


if __name__ == "__main__":
    main()