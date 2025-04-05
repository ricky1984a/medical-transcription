# app/create_postgres_tables.py
import os
import sys
import logging
import ssl
from urllib.parse import urlparse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()


# Support DATABASE_URL or broken-out env vars
def get_pg_config():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print("Using DATABASE_URL:", db_url)
        result = urlparse(db_url)
        return {
            "database": result.path[1:],
            "user": result.username,
            "password": result.password,
            "host": result.hostname,
            "port": result.port or "5432"
        }
    else:
        print("Using individual POSTGRES_* environment variables")
        return {
            "database": os.getenv("POSTGRES_DATABASE"),
            "user": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD"),
            "host": os.getenv("POSTGRES_HOST"),
            "port": os.getenv("POSTGRES_PORT", "5432")
        }


def connect_postgres():
    """Connect to PostgreSQL database using pg8000"""
    try:
        import pg8000
        config = get_pg_config()

        # Create SSL context for secure connections
        ssl_context = ssl.create_default_context()
        # Don't verify server certificate
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Connect with pg8000 using ssl_context instead of ssl=True
        conn = pg8000.connect(
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=int(config['port']),
            database=config['database'],
            ssl_context=ssl_context  # Use proper SSL context
        )

        print(f"✅ Connected to PostgreSQL database: {config['database']}")
        return conn
    except ImportError:
        print("❌ pg8000 module not found. Please install it with: pip install pg8000")
        sys.exit(1)
    except Exception as e:
        print(f"❌ PostgreSQL connection error: {e}")

        # Try a fallback approach with simple ssl=True
        try:
            print("Trying fallback connection method...")
            conn = pg8000.connect(
                user=config['user'],
                password=config['password'],
                host=config['host'],
                port=int(config['port']),
                database=config['database'],
                ssl=True  # Fallback to simple bool
            )
            print(f"✅ Connected to PostgreSQL database (fallback): {config['database']}")
            return conn
        except Exception as e2:
            print(f"❌ Fallback connection also failed: {e2}")
            sys.exit(1)


def create_tables(conn):
    """Create tables in PostgreSQL"""
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE,
        email VARCHAR(255) UNIQUE,
        hashed_password VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        password_reset_token VARCHAR(255),
        password_reset_expires TIMESTAMP WITH TIME ZONE,
        password_changed_at TIMESTAMP WITH TIME ZONE,
        login_attempts INTEGER DEFAULT 0,
        last_login_at TIMESTAMP WITH TIME ZONE
    );
    """)

    # Create transcriptions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transcriptions (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255),
        content TEXT,
        user_id INTEGER REFERENCES users(id),
        file_path VARCHAR(255),
        language VARCHAR(10) DEFAULT 'en',
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)

    # Create translations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS translations (
        id SERIAL PRIMARY KEY,
        transcription_id INTEGER REFERENCES transcriptions(id) ON DELETE CASCADE,
        content TEXT,
        source_language VARCHAR(10),
        target_language VARCHAR(10),
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)

    # Create audit logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        resource_type VARCHAR(50) NOT NULL,
        resource_id INTEGER NOT NULL,
        action VARCHAR(50) NOT NULL,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        ip_address VARCHAR(45),
        user_agent VARCHAR(255),
        description TEXT
    );
    """)

    conn.commit()
    print("✅ Tables created successfully!")


def main():
    try:
        pg_conn = connect_postgres()
        create_tables(pg_conn)
        pg_conn.close()
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()