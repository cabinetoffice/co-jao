"""
Django management command to test database connectivity.
This command tests the database connection using Django's ORM and provides
detailed diagnostics for troubleshooting connection issues.
"""

import os
import sys
import time
from django.core.management.base import BaseCommand
from django.db import connection, connections
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class Command(BaseCommand):
    help = 'Test database connectivity and perform basic diagnostics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            default='default',
            help='Database alias to test (default: default)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        database_alias = options.get('database', 'default')

        self.stdout.write(self.style.HTTP_INFO('='*60))
        self.stdout.write(self.style.HTTP_INFO(' JAO Backend Database Connection Test'))
        self.stdout.write(self.style.HTTP_INFO('='*60))

        # Test basic Django configuration
        self.test_django_config()

        # Test database configuration
        self.test_database_config(database_alias)

        # Test database connection
        success = self.test_database_connection(database_alias)

        if success:
            self.stdout.write(
                self.style.SUCCESS('\n🎉 Database connection test PASSED!')
            )
            return 0
        else:
            self.stdout.write(
                self.style.ERROR('\n💥 Database connection test FAILED!')
            )
            return 1

    def test_django_config(self):
        """Test basic Django configuration."""
        self.stdout.write(self.style.HTTP_INFO('\n--- Django Configuration Test ---'))

        try:
            # Test settings
            self.stdout.write(f"✅ Settings module: {settings.SETTINGS_MODULE}")
            self.stdout.write(f"✅ Debug mode: {settings.DEBUG}")
            self.stdout.write(f"✅ Environment: {os.getenv('ENV', 'not set')}")

            # Test database configuration exists
            if hasattr(settings, 'DATABASES'):
                self.stdout.write(f"✅ DATABASES configured with {len(settings.DATABASES)} database(s)")
                if self.verbose:
                    for alias, config in settings.DATABASES.items():
                        engine = config.get('ENGINE', 'unknown')
                        name = config.get('NAME', 'unknown')
                        host = config.get('HOST', 'unknown')
                        port = config.get('PORT', 'unknown')
                        self.stdout.write(f"   - {alias}: {engine} at {host}:{port}/{name}")
            else:
                self.stdout.write(self.style.ERROR("❌ DATABASES not configured"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Django configuration error: {e}"))

    def test_database_config(self, database_alias):
        """Test database configuration."""
        self.stdout.write(self.style.HTTP_INFO(f'\n--- Database Configuration Test ({database_alias}) ---'))

        try:
            if database_alias not in settings.DATABASES:
                self.stdout.write(self.style.ERROR(f"❌ Database alias '{database_alias}' not found"))
                return False

            db_config = settings.DATABASES[database_alias]

            # Display configuration (safely)
            engine = db_config.get('ENGINE', 'Not set')
            name = db_config.get('NAME', 'Not set')
            host = db_config.get('HOST', 'Not set')
            port = db_config.get('PORT', 'Not set')
            user = db_config.get('USER', 'Not set')

            self.stdout.write(f"✅ Engine: {engine}")
            self.stdout.write(f"✅ Database: {name}")
            self.stdout.write(f"✅ Host: {host}")
            self.stdout.write(f"✅ Port: {port}")
            self.stdout.write(f"✅ User: {user}")

            # Check if password is set (don't display it)
            password = db_config.get('PASSWORD')
            if password:
                self.stdout.write(f"✅ Password: {'*' * len(str(password))}")
            else:
                self.stdout.write(self.style.WARNING("⚠️  Password: Not set"))

            # Display connection options if any
            options = db_config.get('OPTIONS', {})
            if options:
                self.stdout.write(f"✅ Options: {list(options.keys())}")

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Database configuration error: {e}"))
            return False

    def test_database_connection(self, database_alias):
        """Test actual database connection."""
        self.stdout.write(self.style.HTTP_INFO(f'\n--- Database Connection Test ({database_alias}) ---'))

        try:
            # Get database connection
            db_connection = connections[database_alias]

            # Test connection
            start_time = time.time()

            with db_connection.cursor() as cursor:
                # Test 1: Simple query
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                connect_time = time.time() - start_time

                self.stdout.write(f"✅ Basic connection successful")
                self.stdout.write(f"   Connection time: {connect_time:.3f} seconds")
                self.stdout.write(f"   Query result: {result}")

                # Test 2: Database version
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                self.stdout.write(f"✅ Database version: {version[:100]}...")

                # Test 3: Current database and user
                cursor.execute("SELECT current_database(), current_user")
                db_info = cursor.fetchone()
                self.stdout.write(f"✅ Current database: {db_info[0]}")
                self.stdout.write(f"✅ Current user: {db_info[1]}")

                # Test 4: Check connection info
                cursor.execute("SELECT inet_server_addr(), inet_server_port(), pg_backend_pid()")
                conn_info = cursor.fetchone()
                self.stdout.write(f"✅ Server IP: {conn_info[0]}")
                self.stdout.write(f"✅ Server Port: {conn_info[1]}")
                self.stdout.write(f"✅ Backend PID: {conn_info[2]}")

                # Test 5: Check for pgvector extension
                cursor.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_extension WHERE extname = 'vector'
                    )
                """)
                has_pgvector = cursor.fetchone()[0]
                if has_pgvector:
                    self.stdout.write("✅ pgvector extension is installed")
                else:
                    self.stdout.write(self.style.WARNING("⚠️  pgvector extension is not installed"))

                # Test 6: Check Django tables
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name LIKE 'django_%'
                """)
                django_tables = cursor.fetchone()[0]
                self.stdout.write(f"✅ Django tables found: {django_tables}")

                if django_tables == 0:
                    self.stdout.write(self.style.WARNING("⚠️  No Django tables found - run migrations?"))

                # Test 7: Check applied migrations
                try:
                    cursor.execute("""
                        SELECT COUNT(*) FROM information_schema.tables
                        WHERE table_name = 'django_migrations'
                    """)
                    has_migrations_table = cursor.fetchone()[0] > 0

                    if has_migrations_table:
                        cursor.execute("SELECT COUNT(*) FROM django_migrations")
                        migration_count = cursor.fetchone()[0]
                        self.stdout.write(f"✅ Applied migrations: {migration_count}")
                    else:
                        self.stdout.write(self.style.WARNING("⚠️  django_migrations table not found"))

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠️  Could not check migrations: {e}"))

                # Test 8: Test transaction
                cursor.execute("BEGIN")
                cursor.execute("SELECT 1")
                cursor.execute("ROLLBACK")
                self.stdout.write("✅ Transaction test successful")

            # Test Django ORM connection
            self.stdout.write(self.style.HTTP_INFO('\n--- Django ORM Test ---'))

            try:
                # Test Django's connection
                from django.db import connection as django_connection

                with django_connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    self.stdout.write("✅ Django ORM connection successful")

                # Test connection close/reopen
                django_connection.close()
                with django_connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    self.stdout.write("✅ Django connection close/reopen successful")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Django ORM test failed: {e}"))
                return False

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Database connection failed: {e}"))

            # Provide troubleshooting hints
            self.stdout.write(self.style.HTTP_INFO('\n--- Troubleshooting Hints ---'))
            error_str = str(e).lower()

            if 'connection refused' in error_str:
                self.stdout.write("💡 Connection refused - check if database is running")
                self.stdout.write("💡 Verify security groups allow port 5432")

            elif 'timeout' in error_str:
                self.stdout.write("💡 Connection timeout - check network connectivity")
                self.stdout.write("💡 Verify security groups and NACLs")

            elif 'authentication failed' in error_str:
                self.stdout.write("💡 Authentication failed - check username/password")
                self.stdout.write("💡 Verify database user exists and has permissions")

            elif 'database' in error_str and 'does not exist' in error_str:
                self.stdout.write("💡 Database does not exist - check database name")
                self.stdout.write("💡 Verify database was created successfully")

            elif 'name or service not known' in error_str:
                self.stdout.write("💡 DNS resolution failed - check database hostname")
                self.stdout.write("💡 Verify VPC DNS settings")

            else:
                self.stdout.write(f"💡 General error: {e}")

            return False

        finally:
            # Clean up connection
            try:
                db_connection.close()
            except:
                pass
