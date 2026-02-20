#!/usr/bin/env python
"""Check MySQL connection and database status"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zeno_time.settings')

try:
    import django
    django.setup()
    
    from django.db import connection
    from django.conf import settings
    
    print("=" * 60)
    print("MySQL Connection Status Check")
    print("=" * 60)
    print()
    
    # Get database configuration
    db_config = settings.DATABASES['default']
    print(f"Database Engine: {db_config['ENGINE']}")
    print(f"Database Name: {db_config['NAME']}")
    print(f"Database User: {db_config['USER']}")
    print(f"Database Host: {db_config['HOST']}")
    print(f"Database Port: {db_config['PORT']}")
    print()
    
    # Test connection
    try:
        cursor = connection.cursor()
        
        # Get MySQL version and connection info
        cursor.execute("SELECT VERSION()")
        mysql_version = cursor.fetchone()[0]
        
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()[0]
        
        cursor.execute("SELECT USER()")
        current_user = cursor.fetchone()[0]
        
        cursor.execute("SELECT CONNECTION_ID()")
        connection_id = cursor.fetchone()[0]
        
        print("[OK] Connection Status: ACTIVE")
        print(f"[OK] MySQL Version: {mysql_version}")
        print(f"[OK] Connected Database: {current_db}")
        print(f"[OK] Connected User: {current_user}")
        print(f"[OK] Connection ID: {connection_id}")
        print()
        
        # Count tables
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE()
        """)
        table_count = cursor.fetchone()[0]
        
        # Get table list
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE()
            ORDER BY table_name
            LIMIT 15
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"[OK] Total Tables: {table_count}")
        print(f"[OK] Sample Tables: {', '.join(tables[:10])}")
        if table_count > 10:
            print(f"     ... and {table_count - 10} more tables")
        print()
        
        # Check for Django tables
        django_tables = ['django_migrations', 'django_content_type', 'auth_user', 'accounts_user']
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE()
            AND table_name IN ('django_migrations', 'django_content_type', 'auth_user', 'accounts_user')
        """)
        found_django_tables = [row[0] for row in cursor.fetchall()]
        
        if found_django_tables:
            print("[OK] Django Core Tables: Found")
            print(f"     {', '.join(found_django_tables)}")
        print()
        
        # Check migrations status
        try:
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            migration_count = cursor.fetchone()[0]
            print(f"[OK] Applied Migrations: {migration_count}")
        except Exception as e:
            print(f"[WARN] Migrations table check: {e}")
        
        print()
        print("=" * 60)
        print("[SUCCESS] MySQL Server is CONNECTED and RUNNING PROPERLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Connection Error: {e}")
        print()
        print("=" * 60)
        print("[FAILED] MySQL Server Connection FAILED")
        print("=" * 60)
        sys.exit(1)
        
except ImportError as e:
    print(f"✗ Django Import Error: {e}")
    sys.exit(1)
