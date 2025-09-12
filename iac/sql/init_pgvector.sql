-- Check if pgvector extension is available
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_available_extensions WHERE name = 'pgvector'
    ) THEN
        EXECUTE 'CREATE EXTENSION IF NOT EXISTS pgvector';
    ELSE
        RAISE NOTICE 'pgvector extension is not available on this RDS instance. Vector operations will not be available.';
    END IF;
END $$;

-- Create user table if Django's auth will be used
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_tables
        WHERE schemaname = 'public'
        AND tablename = 'auth_user'
    ) THEN
        RAISE NOTICE 'Django auth_user table will be created by Django migrations';
    END IF;
END $$;

-- Grant permissions
DO $$
BEGIN
    EXECUTE format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %I', current_user);
    EXECUTE format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %I', current_user);
END $$;

-- Add permissions for pgvector
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO PUBLIC;
